"""MkDocs-Hooks für shelly_script (GitHub Pages).

- kleingeschriebene readme.md wie README.md als Ordner-Startseite behandeln
- Seitentitel aus der ersten '# '-Überschrift nehmen, auch wenn davor Badges stehen
- Skripte/Konfig-Dateien (siehe extra.skip_extensions) nicht veröffentlichen
- Links auf nicht veröffentlichte Dateien/Ordner auf GitHub umbiegen
- Startseite jedes Ordners in der Navigation nach oben sortieren
- eigenes Stylesheet (.mkdocs/extra.css) einbinden, ohne es in shelly_script abzulegen
"""
import os
import posixpath
import re

from mkdocs.structure.files import File
from mkdocs.structure.nav import Section
from mkdocs.structure.pages import Page

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = "assets/zendure.css"

_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)
_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
_FENCE = re.compile(r"(```.*?```)", re.DOTALL)


def on_config(config):
    config.extra_css.append(CSS)
    return config


def on_files(files, config):
    docs = os.path.abspath(config["docs_dir"])
    skip = {e.lower() for e in config.extra.get("skip_extensions", [])}

    for f in list(files):
        # nur Dateien aus shelly_script betreffen, niemals Theme-Dateien
        if not f.abs_src_path or not os.path.abspath(f.abs_src_path).startswith(docs + os.sep):
            continue
        ext = os.path.splitext(f.src_uri)[1].lower()
        if ext in skip:
            files.remove(f)
            continue
        folder, name = posixpath.split(f.src_uri)
        if name.lower() == "readme.md" and name != "README.md":
            if files.get_file_from_path(posixpath.join(folder, "index.md")):
                continue
            f.dest_uri = posixpath.join(folder, "index.html")
            f.url = (folder + "/") if folder else "./"

    files.append(File.generated(config, CSS, abs_src_path=os.path.join(HERE, "extra.css")))
    return files


def _is_index(item):
    if not isinstance(item, Page):
        return False
    name = posixpath.basename(item.file.src_uri).lower()
    return name in ("readme.md", "index.md")


def _sort(items):
    items.sort(key=lambda i: 0 if _is_index(i) else 1)
    for i in items:
        if isinstance(i, Section):
            _sort(i.children)


def on_nav(nav, config, files):
    _sort(nav.items)
    return nav


def _rewrite_links(markdown, page, config, files):
    repo = (config.get("repo_url") or "").rstrip("/")
    if not repo:
        return markdown
    root = os.path.dirname(config["config_file_path"])
    docs_rel = os.path.relpath(config["docs_dir"], root).replace(os.sep, "/")
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
