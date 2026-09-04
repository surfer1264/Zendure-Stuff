#!/usr/bin/env python3
"""
swap_config.py - tauscht den CONFIG-Block in einem Shelly-Skript aus.

Nimmt ein Ziel-Skript (z.B. eine frisch heruntergeladene generische Version)
und ersetzt darin den Block

    let CONFIG = { ... };

durch den CONFIG-Block aus einer anderen Datei (z.B. deiner alten,
fertig konfigurierten Version oder einer reinen Config-Datei).

Beispiele:
    python3 swap_config.py neu.js --config-from alt.js -o fertig.js
    python3 swap_config.py neu.js --config-from meine_config.txt --in-place
    python3 swap_config.py neu.js --config-from alt.js --check

Der Rest des Skripts (auch die minifizierte Zeile darunter) bleibt
unveraendert. Zeilenenden des Zielskripts werden beibehalten.
"""

import argparse
import re
import shutil
import sys

START_RE = re.compile(r"(?m)^[ \t]*let[ \t]+CONFIG[ \t]*=[ \t]*\{")


def find_config_block(text, source_name):
    """Liefert (start, end) des kompletten 'let CONFIG = {...};'-Blocks."""
    m = START_RE.search(text)
    if not m:
        raise ValueError(
            "In %s wurde kein 'let CONFIG = {' gefunden." % source_name
        )
    start = m.start()
    i = text.index("{", m.start())

    depth = 0
    state = "code"  # code | line_comment | block_comment | ' | " | `
    n = len(text)

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if state == "code":
            if c == "/" and nxt == "/":
                state = "line_comment"
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if c in "'\"`":
                state = c
                i += 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    # optionales Semikolon mitnehmen
                    j = end
                    while j < n and text[j] in " \t":
                        j += 1
                    if j < n and text[j] == ";":
                        end = j + 1
                    return start, end
        elif state == "line_comment":
            if c == "\n":
                state = "code"
        elif state == "block_comment":
            if c == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
        else:  # in einem String
            if c == "\\":
                i += 2
                continue
            if c == state:
                state = "code"

        i += 1

    raise ValueError(
        "In %s ist der CONFIG-Block nicht geschlossen (fehlende '}')." % source_name
    )


def dominant_newline(text):
    crlf = text.count("\r\n")
    cr = text.count("\r") - crlf
    lf = text.count("\n") - crlf
    if crlf >= lf and crlf >= cr:
        return "\r\n"
    if cr > lf:
        return "\r"
    return "\n"


def normalise_newlines(text, newline):
    plain = text.replace("\r\n", "\n").replace("\r", "\n")
    return plain.replace("\n", newline)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def extract_new_config(path):
    """Holt den CONFIG-Block aus einer Datei - egal ob ganzes Skript
    oder nur der Block."""
    text = read(path)
    start, end = find_config_block(text, path)
    return text[start:end]


def sanity_check(block, label):
    """Ein paar leichte Plausibilitaetspruefungen, damit man sich nicht
    versehentlich Platzhalter ins laufende Skript holt."""
    warnings = []
    if "<" in block and ">" in block:
        for line in block.splitlines():
            if re.search(r"<[^>]{3,}>", line) and not line.strip().startswith("//"):
                warnings.append("Platzhalter uebrig: " + line.strip())
    if "devices" not in block:
        warnings.append("Kein 'devices'-Array im %s gefunden." % label)
    return warnings


def main():
    p = argparse.ArgumentParser(
        description="Tauscht den CONFIG-Block in einem Shelly-Skript aus."
    )
    p.add_argument("target", help="Skript, in dem der CONFIG-Block ersetzt wird")
    p.add_argument(
        "--config-from",
        required=True,
        metavar="DATEI",
        help="Datei mit dem neuen CONFIG-Block (ganzes Skript oder nur der Block)",
    )
    p.add_argument("-o", "--output", metavar="DATEI", help="Zieldatei (Standard: stdout)")
    p.add_argument(
        "--in-place",
        action="store_true",
        help="Zieldatei direkt ueberschreiben (legt .bak an)",
    )
    p.add_argument(
        "--no-backup", action="store_true", help="Bei --in-place kein .bak anlegen"
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Nur pruefen und Zusammenfassung zeigen, nichts schreiben",
    )
    args = p.parse_args()

    try:
        target_text = read(args.target)
        start, end = find_config_block(target_text, args.target)
        new_block = extract_new_config(args.config_from)
    except (OSError, ValueError) as err:
        print("Fehler: %s" % err, file=sys.stderr)
        return 1

    old_block = target_text[start:end]
    newline = dominant_newline(target_text)
    new_block_nl = normalise_newlines(new_block, newline)
    result = target_text[:start] + new_block_nl + target_text[end:]

    for w in sanity_check(new_block, "neuen CONFIG-Block"):
        print("Warnung: %s" % w, file=sys.stderr)

    print(
        "CONFIG-Block ersetzt: %d -> %d Zeilen (Rest des Skripts unveraendert, %d Zeichen)"
        % (
            len(old_block.splitlines()),
            len(new_block_nl.splitlines()),
            len(target_text) - len(old_block),
        ),
        file=sys.stderr,
    )

    if args.check:
        return 0

    if args.in_place:
        if not args.no_backup:
            shutil.copy2(args.target, args.target + ".bak")
            print("Backup: %s.bak" % args.target, file=sys.stderr)
        write(args.target, result)
        print("Geschrieben: %s" % args.target, file=sys.stderr)
    elif args.output:
        write(args.output, result)
        print("Geschrieben: %s" % args.output, file=sys.stderr)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
