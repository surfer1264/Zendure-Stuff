"""MkDocs-Hooks für shelly_script:
- kleingeschriebene readme.md wie README.md als Ordner-Startseite behandeln
- Seitentitel aus der ersten '# '-Überschrift nehmen, auch wenn davor Badges/Text stehen
- Links auf Dateien/Ordner, die nicht veröffentlicht werden (Skripte, Ordner),
  auf GitHub umbiegen, damit sie auf der Seite nicht ins Leere führen
"""
import os
import posixpath
import re

_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)
_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
_FENCE = re.compile(r"(```.*?```)", re.DOTALL)


def on_files(files, config):
    for f in files:
        if not f.src_uri.endswith(".md"):
            continue
        folder, name = posixpath.split(f.src_uri)
        if name.lower() == "readme.md" and name != "README.md":
            if files.get_file_from_path(posixpath.join(folder, "index.md")):
                continue
            f.dest_uri = posixpath.join(folder, "index.html")
            f.url = (folder + "/") if folder else "./"
    return files


def _github_base(config):
    repo = (config.get("repo_url") or "").rstrip("/")
    docs = os.path.relpath(config["docs_dir"], os.path.dirname(config["config_file_path"]))
    return repo, docs.replace(os.sep, "/")


def _rewrite_links(markdown, page, config, files):
    repo, docs_rel = _github_base(config)
    if not repo:
        return markdown
    page_dir = posixpath.dirname(page.file.src_uri)

    def fix(m):
        target = m.group(2)
        if re.match(r"^([a-z]+:|#|/)", target, re.I):
            return m.group(0)
        path, _, anchor = target.partition("#")
        rel = posixpath.normpath(posixpath.join(page_dir, path)).lstrip("./") if path else ""
        if not rel or rel.startswith(".."):
            return m.group(0)
        f = files.get_file_from_path(rel)
        if f is not None and f.inclusion.is_included():
            return m.group(0)  # wird veröffentlicht -> Link bleibt
        local = os.path.join(config["docs_dir"], rel)
        if os.path.isdir(local):
            kind = "tree"
        elif os.path.isfile(local):
            kind = "blob"
        else:
            return m.group(0)  # existiert nicht -> MkDocs warnt
        url = f"{repo}/{kind}/main/{docs_rel}/{rel}" + (f"#{anchor}" if anchor else "")
        return m.group(1) + url + m.group(3)

    parts = _FENCE.split(markdown)
    for i in range(0, len(parts), 2):  # nur außerhalb von Code-Blöcken
        parts[i] = _LINK.sub(fix, parts[i])
    return "".join(parts)


def on_page_markdown(markdown, page, config, files):
    if "title" not in page.meta:
        m = _H1.search(_FENCE.sub("", markdown))
        if m:
            page.meta["title"] = m.group(1).strip()
    return _rewrite_links(markdown, page, config, files)
