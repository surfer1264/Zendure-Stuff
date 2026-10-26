#!/usr/bin/env python3
"""
Minifiziert ein Shelly-mJS-Skript, laesst dabei den "let CONFIG = { ... };"
Block Byte-fuer-Byte unveraendert (Kommentare, Formatierung bleiben erhalten).

Verwendung:
    python3 minify_keep_config.py <input.js> [output.min.js]

Vorgehen:
    1. CONFIG-Block strukturell erkennen (Klammerzaehlung, nicht Zeilennummer).
    2. Alles VOR und NACH dem Block mit Terser minifizieren
       (--ecma 5, KEIN --compress, KEIN --mangle -> nur Kommentare/Whitespace weg).
    3. Wieder zusammensetzen: minified(davor) + CONFIG-Block original + minified(danach).
    4. Verifikation: Terser parst das Gesamtergebnis nochmal (Syntax-Check),
       Anzahl 'function'/'let' vorher==nachher, keine Arrow-Functions/Template-Strings.
"""
import re
import subprocess
import sys
import os
import tempfile
import shutil


def find_npx():
    """Findet den npx-Ausfuehrungspfad plattformunabhaengig.

    Unter Windows liegt npx als 'npx.cmd' vor. subprocess.run(["npx", ...])
    ohne shell=True nutzt CreateProcess direkt, die .cmd/.bat-Dateien nicht
    ueber den blossen Namen findet (WinError 2), obwohl 'npx' in der
    Konsole normal funktioniert. shutil.which() macht dieselbe PATH-/
    PATHEXT-Aufloesung wie die Shell und liefert unter Windows z.B.
    'C:\\...\\npx.cmd', unter Linux/Mac '/usr/bin/npx'.
    """
    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError(
            "npx wurde nicht gefunden. Ist Node.js/npm installiert und im PATH?"
        )
    return npx


NPX = find_npx()


def find_config_block(text):
    """Findet Start/Ende (Zeichen-Indizes) von 'let CONFIG = { ... };' per Klammerzaehlung."""
    m = re.search(r'^let CONFIG = \{', text, re.MULTILINE)
    if not m:
        raise ValueError("Kein 'let CONFIG = {' gefunden - Skript-Struktur hat sich geaendert?")

    start = m.start()
    brace_start = text.index('{', start)

    depth = 0
    i = brace_start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                # ';' direkt nach der schliessenden Klammer mit einschliessen, falls vorhanden
                end = i + 1
                if end < len(text) and text[end] == ';':
                    end += 1
                return start, end
        i += 1

    raise ValueError("Ende des CONFIG-Blocks nicht gefunden (unbalancierte Klammern?)")


def terser_minify(js_text, tmp_path):
    """Minifiziert ein JS-Snippet konservativ (kein compress/mangle)."""
    in_path = tmp_path + ".in.js"
    out_path = tmp_path + ".out.js"
    with open(in_path, "w", encoding="utf-8") as f:
        f.write(js_text)

    result = subprocess.run(
        [NPX, "terser", in_path, "-o", out_path, "--ecma", "5", "-f", "beautify=false"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Terser-Fehler:\n{result.stderr}")

    with open(out_path, encoding="utf-8") as f:
        return f.read()


def verify(original_rest, minified_rest, full_output, tmp_dir):
    checks = []

    def count(pattern, text):
        return len(re.findall(pattern, text))

    checks.append(("keine Arrow-Functions (=>)", count(r'=>', minified_rest) == 0))
    checks.append(("keine Template-Strings (`)", count(r'`', minified_rest) == 0))
    checks.append((
        "Anzahl 'function' unveraendert",
        count(r'\bfunction\b', original_rest) == count(r'\bfunction\b', minified_rest)
    ))
    checks.append((
        "Anzahl 'let'-Deklarationen unveraendert",
        count(r'\blet\s+[a-zA-Z_]', original_rest) == count(r'\blet\s+[a-zA-Z_]', minified_rest)
    ))

    # Terser parst das GESAMTE Ergebnis nochmal als reinen Syntax-Check
    tmp_check = os.path.join(tmp_dir, "_verify_full")
    with open(tmp_check + ".js", "w", encoding="utf-8") as f:
        f.write(full_output)
    result = subprocess.run(
        [NPX, "terser", tmp_check + ".js", "-o", tmp_check + ".out.js", "--ecma", "5"],
        capture_output=True, text=True
    )
    checks.append(("Gesamtdatei erneut syntaktisch gueltig (Terser-Reparse)", result.returncode == 0))

    print("\n=== Verifikation ===")
    all_ok = True
    for label, ok in checks:
        print(f"  [{'OK' if ok else 'FEHLER'}] {label}")
        all_ok = all_ok and ok
    return all_ok


def main():
    if len(sys.argv) < 2:
        print("Verwendung: python3 minify_keep_config.py <input.js> [output.min.js]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else (
        os.path.splitext(input_path)[0] + ".min.js"
    )

    # newline='' verhindert Pythons automatische Universal-Newline-Uebersetzung
    # (sonst wuerde CRLF beim Lesen still zu LF - der CONFIG-Block soll aber
    # wirklich Byte-fuer-Byte, inkl. Original-Zeilenenden, erhalten bleiben).
    with open(input_path, encoding="utf-8", newline="") as f:
        text = f.read()

    cfg_start, cfg_end = find_config_block(text)
    before = text[:cfg_start]
    config_block = text[cfg_start:cfg_end]
    after = text[cfg_end:]

    print(f"CONFIG-Block erkannt: Zeichen {cfg_start}-{cfg_end} "
          f"({len(config_block.splitlines())} Zeilen, wird NICHT veraendert)")

    with tempfile.TemporaryDirectory(prefix="minify_keep_config_", dir=os.getcwd()) as tmp_dir:
        before_min = terser_minify(before, os.path.join(tmp_dir, "_part_before")) if before.strip() else ""
        after_min = terser_minify(after, os.path.join(tmp_dir, "_part_after")) if after.strip() else ""

        output = (before_min + "\n" if before_min else "") + \
                 config_block.strip() + "\n\n" + \
                 after_min.strip() + "\n"

        ok = verify(before + after, before_min + after_min, output, tmp_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    orig_size = len(text.encode("utf-8"))
    new_size = len(output.encode("utf-8"))
    saved = orig_size - new_size

    print(f"\n{input_path}: {orig_size} Bytes")
    print(f"{output_path}: {new_size} Bytes")
    print(f"Ersparnis: {saved} Bytes ({saved / orig_size * 100:.1f}%)")

    if not ok:
        print("\nACHTUNG: mindestens eine Verifikation ist fehlgeschlagen - Ergebnis pruefen!")
        sys.exit(2)


if __name__ == "__main__":
    main()