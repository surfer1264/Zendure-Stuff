#!/usr/bin/env python3
"""
build_manifest.py - erzeugt versions.json fuer den Zendure-Multi-Configurator
und den lokalen Helfer. Laeuft im GitHub-Workflow "Versions-Manifest",
nicht lokal. Nur Python-Standardbibliothek.

Aufruf:
    python3 build_manifest.py <altes_manifest.json|-> <neues_manifest.json>

    "-" als altes Manifest = es gibt noch keins (erster Lauf).

Was das Script tut:
  1. Sucht alle shelly_script/**/*_mini.js. Dateien ohne SCRIPT_TYPE werden
     uebersprungen (z.B. alte Scripte, die nicht zum Update-System gehoeren).
  2. Liest je Script SCRIPT_TYPE, VERSION und CONFIG_SCHEMA.
  3. Berechnet Groesse, Code-Hash (ohne CONFIG-Block, siehe code_hash())
     und die Liste der Feldnamen im CONFIG-Block.
  4. Liest optional CHANGELOG.md im selben Ordner wie die Mini-Datei.
  5. Vergleicht mit dem alten Manifest (Plausibilitaet, History).
  6. Schreibt das neue Manifest - aber nur, wenn KEIN Fehler auftrat.
     Bei einem Fehler endet das Script mit Exit-Code 1 und schreibt nichts;
     das alte Manifest bleibt dann unveraendert gueltig.

Changelog (optional, je Script-Ordner): CHANGELOG.md oder jede .md mit
"chang...log" im Namen. Ueberschriften "## 5.0.8" oder "## Changelog 5.0.8":
    ## 5.0.8
    - Kurzer Text fuer Nutzer (max. 3 Zeilen werden uebernommen)
    - Noch ein Punkt
    > Optionaler Hinweis, den der Nutzer vor dem Update bestaetigen muss

manifest_meta.json (optional, unter shelly_script/):
    {
      "helperMin": "1.0",
      "requires": { "zdmc-zendash-watch": { "zdmc-controller": ">=5.0" } }
    }

Umgebungsvariablen (vom Workflow gesetzt):
    GITHUB_SHA         Commit, aus dem die Dateien stammen
    GITHUB_REPOSITORY  z.B. surfer1264/Zendure-Stuff
"""

import datetime
import glob
import hashlib
import json
import os
import re
import sys
import urllib.parse

MANIFEST_VERSION = 1
HASH_ALGO = "sha256-noconfig-v1"
HISTORY_MAX = 10
CHANGES_MAX = 3
SCRIPT_GLOB = "shelly_script/**/*_mini.js"
META_FILE = "shelly_script/manifest_meta.json"
CONFIG_PLACEHOLDER = "let CONFIG = __CONFIG__;"

RE_TYPE = re.compile(r"""\bSCRIPT_TYPE\s*=\s*["']([^"']+)["']""")
RE_VERSION = re.compile(r"""\bVERSION\s*=\s*["']([^"']+)["']""")
RE_SCHEMA = re.compile(r"""\bCONFIG_SCHEMA\s*=\s*(\d+)""")
RE_CONFIG_START = re.compile(r"^let CONFIG\s*=\s*\{", re.MULTILINE)
RE_CHANGELOG_NAME = re.compile(r"chang\w*log", re.IGNORECASE)
RE_CHANGELOG_HEAD = re.compile(r"^#{2,3}\s+(?:[^\d\s]\S*\s+)*v?(\d+(?:\.\d+)+)\b")

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print("::error::" + msg)


def warn(msg):
    warnings.append(msg)
    print("::warning::" + msg)


# ---------------------------------------------------------------------
# CONFIG-Block finden - beachtet Strings und Kommentare, damit eine
# Klammer in einem Kommentar oder einer URL die Zaehlung nicht verdirbt.
# ---------------------------------------------------------------------
def find_config_block(text):
    m = RE_CONFIG_START.search(text)
    if not m:
        return None
    i = m.end() - 1          # Position der oeffnenden {
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            i += 1
            while i < n and text[i] != c:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < n and text[end] == ";":
                    end += 1
                return m.start(), end
        i += 1
    return None


def strip_strings_and_comments(text):
    """Ersetzt Strings und Kommentare durch Leerzeichen (fuer die Feldliste)."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            i += 1
            while i < n and text[i] != c:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append(" ")
            continue
        out.append(c)
        i += 1
    return "".join(out)


def normalize(text):
    """Vereinheitlicht so, wie es auch der Helper fuer Shelly-Code tun muss."""
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip()


def code_hash(text):
    """HASH-DEFINITION sha256-noconfig-v1 (der Helper muss exakt so rechnen):
    1. BOM entfernen, Zeilenenden auf LF, Leerraum am Dateiende entfernen
    2. den kompletten Block 'let CONFIG = {...};' durch
       'let CONFIG = __CONFIG__;' ersetzen
    3. SHA-256 ueber UTF-8, hex
    """
    t = normalize(text)
    rng = find_config_block(t)
    if rng is None:
        return None
    t = t[:rng[0]] + CONFIG_PLACEHOLDER + t[rng[1]:]
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def config_keys(text):
    t = normalize(text)
    rng = find_config_block(t)
    if rng is None:
        return []
    body = strip_strings_and_comments(t[rng[0]:rng[1]])
    return sorted(set(re.findall(r"([A-Za-z_$][\w$]*)\s*:", body)))


def version_tuple(v):
    parts = []
    for p in re.split(r"[.\-]", str(v)):
        parts.append((0, int(p)) if p.isdigit() else (1, p))
    return tuple(parts)


def find_changelog(folder):
    """Changelog im Script-Ordner: bevorzugt CHANGELOG.md, sonst jede .md,
    deren Name 'chang...log' enthaelt (z.B. 'ChangLog MultiDevice.md')."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return None
    for n in names:
        if n.lower() == "changelog.md":
            return os.path.join(folder, n)
    for n in names:
        if n.lower().endswith(".md") and RE_CHANGELOG_NAME.search(n):
            return os.path.join(folder, n)
    return None


def read_changelog(folder, version):
    """Liefert (changes, notice, pfad). Erkennt Ueberschriften wie
    '## 5.0.8', '## v5.0.8', '## Changelog 5.0.8', '## Changlog 5.0.6'.
    changes: Aufzaehlungspunkte (- / *) des Abschnitts; gibt es keine,
    die ersten Prosa-Zeilen. Zeilen mit '>' werden zum Hinweis (notice)."""
    path = find_changelog(folder)
    if not path:
        return [], None, None
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().replace("\r\n", "\n").split("\n")
    bullets, prose, notice = [], [], []
    inside = found = in_code = False
    for line in lines:
        head = RE_CHANGELOG_HEAD.match(line)
        if head:
            if inside:
                break
            inside = head.group(1) == version
            found = found or inside
            continue
        if not inside:
            continue
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith("#"):
            continue
        if s.startswith(">"):
            notice.append(s.lstrip(">").strip())
        elif s.startswith(("- ", "* ")):
            bullets.append(s[2:].strip())
        else:
            prose.append(s)
    if not found:
        warn("%s: kein Abschnitt zu Version %s - changes bleibt leer." % (path, version))
    changes = bullets or prose
    return changes[:CHANGES_MAX], (" ".join(notice) or None), path.replace(os.sep, "/")


def load_json(path, default):
    if path == "-" or not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as e:
        err("Altes Manifest %s nicht lesbar: %s" % (path, e))
        return default


def raw_url(repo, sha, path):
    return "https://raw.githubusercontent.com/%s/%s/%s" % (repo, sha, path)


# ---------------------------------------------------------------------
def build_entry(path, repo, sha, meta):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    m_type = RE_TYPE.search(text)
    if not m_type:
        print("Uebersprungen (kein SCRIPT_TYPE): " + path)
        return None, None
    stype = m_type.group(1)

    m_ver = RE_VERSION.search(text)
    if not m_ver:
        err("%s: SCRIPT_TYPE vorhanden, aber kein VERSION." % path)
        return stype, None

    m_schema = RE_SCHEMA.search(text)
    schema = int(m_schema.group(1)) if m_schema else None
    if schema is None:
        warn("%s: kein CONFIG_SCHEMA - Schnell-Update fuer diese Version nicht moeglich." % path)

    h = code_hash(text)
    if h is None:
        err("%s: CONFIG-Block nicht gefunden oder unvollstaendig." % path)
        return stype, None

    changes, notice, cl_path = read_changelog(os.path.dirname(path), m_ver.group(1))

    entry = {
        "version": m_ver.group(1),
        "schema": schema,
        "file": path.replace(os.sep, "/"),
        "url": raw_url(repo, sha, path.replace(os.sep, "/")),
        "size": len(text.encode("utf-8")),
        "codeHash": h,
        "configKeys": config_keys(text),
        "changes": changes,
        "notice": notice,
        "changelogUrl": ("https://github.com/%s/blob/main/%s" % (repo, urllib.parse.quote(cl_path))
                         if cl_path else None),
        "requires": (meta.get("requires") or {}).get(stype, {}),
        "history": [],
    }
    return stype, entry


def history_item(e):
    return {k: e.get(k) for k in ("version", "schema", "codeHash", "changes", "notice")}


def merge_with_old(stype, new, old):
    """Plausibilitaet gegen den bisherigen Stand und History fortschreiben."""
    if not old:
        return new

    old_v, new_v = old.get("version"), new["version"]
    same_version = old_v == new_v
    same_code = old.get("codeHash") == new["codeHash"]

    if same_version and same_code:
        # Nichts Relevantes geaendert: alten Eintrag behalten (inkl. url),
        # nur Changelog/Meta duerfen sich nachtraeglich aendern.
        kept = dict(old)
        for k in ("changes", "notice", "changelogUrl", "requires", "file", "configKeys", "schema"):
            kept[k] = new[k]
        if kept["file"] != old.get("file"):
            kept["url"] = new["url"]
        return kept

    if same_version and not same_code:
        err("%s: Code geaendert, aber VERSION %s gleich geblieben - Version hochzaehlen."
            % (stype, new_v))
        return old

    if version_tuple(new_v) < version_tuple(old_v):
        err("%s: VERSION %s ist kleiner als die bisherige %s." % (stype, new_v, old_v))
        return old

    old_s, new_s = old.get("schema"), new["schema"]
    if old_s is not None and new_s is not None:
        if new_s < old_s:
            err("%s: CONFIG_SCHEMA %s ist kleiner als das bisherige %s." % (stype, new_s, old_s))
            return old
        if new_s == old_s and old.get("configKeys") and old["configKeys"] != new["configKeys"]:
            added = sorted(set(new["configKeys"]) - set(old["configKeys"]))
            removed = sorted(set(old["configKeys"]) - set(new["configKeys"]))
            warn("%s: Feldnamen im CONFIG-Block geaendert (neu: %s, entfallen: %s), "
                 "CONFIG_SCHEMA aber gleich (%s) - hochzaehlen vergessen?"
                 % (stype, added or "-", removed or "-", new_s))

    if same_code:
        warn("%s: VERSION %s -> %s, aber Code unveraendert." % (stype, old_v, new_v))

    history = [history_item(old)] + list(old.get("history") or [])
    new["history"] = history[:HISTORY_MAX]
    return new


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    old_path, out_path = sys.argv[1], sys.argv[2]

    repo = os.environ.get("GITHUB_REPOSITORY", "surfer1264/Zendure-Stuff")
    sha = os.environ.get("GITHUB_SHA", "main")

    old_manifest = load_json(old_path, {})
    old_scripts = old_manifest.get("scripts") or {}
    meta = load_json(META_FILE, {})

    scripts = {}
    for path in sorted(glob.glob(SCRIPT_GLOB, recursive=True)):
        stype, entry = build_entry(path, repo, sha, meta)
        if stype is None:
            continue
        if stype in scripts:
            err("SCRIPT_TYPE '%s' kommt mehrfach vor (zuletzt in %s)." % (stype, path))
            continue
        if entry is None:
            continue
        scripts[stype] = merge_with_old(stype, entry, old_scripts.get(stype))
        print("%-22s v%-8s schema %-4s %s" % (
            stype, scripts[stype]["version"], scripts[stype]["schema"], scripts[stype]["file"]))

    for stype in old_scripts:
        if stype not in scripts:
            warn("SCRIPT_TYPE '%s' ist im Repo nicht mehr zu finden - Eintrag entfaellt." % stype)

    if not scripts:
        err("Keine Scripte mit SCRIPT_TYPE gefunden (%s)." % SCRIPT_GLOB)

    if errors:
        print("\n%d Fehler - Manifest wird NICHT aktualisiert." % len(errors))
        return 1

    manifest = {
        "manifestVersion": MANIFEST_VERSION,
        "hashAlgo": HASH_ALGO,
        "generated": None,
        "helperMin": meta.get("helperMin"),
        "scripts": scripts,
    }

    # Unveraendert gegenueber dem alten Manifest? Dann auch den alten
    # Zeitstempel behalten - die Datei ist dann byte-gleich und der
    # Workflow committet nichts.
    old_cmp = dict(old_manifest, generated=None)
    if old_manifest and old_cmp == manifest:
        manifest["generated"] = old_manifest.get("generated")
        print("\nManifest inhaltlich unveraendert.")
    else:
        manifest["generated"] = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("\nManifest geschrieben: %s (%d Script(e), %d Warnung(en))"
          % (out_path, len(scripts), len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
