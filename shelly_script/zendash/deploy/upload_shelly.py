#!/usr/bin/env python3
"""
upload_shelly.py - laedt ein Skript auf einen Shelly (Gen2/Gen3/Gen4).

Ablauf:
  1. Script.List   - vorhandene Skripte holen
  2. Script.Stop   - gleichnamiges altes Skript anhalten
  3. Script.Delete - und loeschen
  4. Script.Create - neues Skript anlegen
  5. Script.PutCode- Code in Haeppchen hochladen (RPC hat ein Groessenlimit)
  6. Script.SetConfig / Script.Start - aktivieren und starten

Beispiele:
  python3 upload_shelly.py skript.js --ip 192.168.178.60
  python3 upload_shelly.py skript.js --ip 192.168.178.60 --name zeroout --no-start
  python3 upload_shelly.py skript.js --ip 192.168.178.60 --dry-run
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


class RpcError(Exception):
    pass


def rpc(ip, method, params=None, timeout=15):
    payload = json.dumps(
        {"id": 1, "method": method, "params": params or {}}
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://%s/rpc" % ip,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:200]
        if err.code == 401:
            raise RpcError(
                "401 - der Shelly verlangt ein Passwort. Auth ist hier nicht "
                "eingebaut; Passwortschutz voruebergehend deaktivieren."
            )
        raise RpcError("%s: HTTP %s %s" % (method, err.code, detail))
    except urllib.error.URLError as err:
        raise RpcError("%s: Shelly %s nicht erreichbar (%s)" % (method, ip, err.reason))

    if "error" in body:
        raise RpcError("%s: %s" % (method, body["error"]))
    return body.get("result", {})


def find_script(ip, name):
    for s in rpc(ip, "Script.List").get("scripts", []):
        if s.get("name") == name:
            return s
    return None


def delete_old(ip, name, dry_run):
    old = find_script(ip, name)
    if not old:
        print("Kein altes Skript namens '%s' vorhanden." % name)
        return
    sid = old["id"]
    print("Altes Skript gefunden: id=%s, name=%s, running=%s"
          % (sid, old.get("name"), old.get("running")))
    if dry_run:
        print("  [DRY-RUN] wuerde gestoppt und geloescht werden")
        return
    if old.get("running"):
        try:
            rpc(ip, "Script.Stop", {"id": sid})
            print("  gestoppt")
        except RpcError as err:
            print("  Stop fehlgeschlagen (egal, wird geloescht): %s" % err)
    rpc(ip, "Script.Delete", {"id": sid})
    print("  geloescht")


def list_scripts(ip):
    scripts = rpc(ip, "Script.List").get("scripts", [])
    if not scripts:
        print("Keine Skripte auf dem Shelly.")
        return
    print("Skripte auf dem Shelly:")
    for s in scripts:
        print("  id=%-3s name=%-24s enable=%-5s running=%s"
              % (s.get("id"), s.get("name"), s.get("enable"), s.get("running")))


def put_code(ip, sid, code, chunk_size, dry_run):
    total = len(code)
    chunks = [code[i:i + chunk_size] for i in range(0, total, chunk_size)]
    print("Uebertrage %d Zeichen in %d Bloecken (%d Zeichen pro Block)..."
          % (total, len(chunks), chunk_size))
    if dry_run:
        print("  [DRY-RUN] nichts uebertragen")
        return
    for n, chunk in enumerate(chunks):
        for attempt in range(3):
            try:
                rpc(ip, "Script.PutCode",
                    {"id": sid, "code": chunk, "append": n > 0})
                break
            except RpcError as err:
                if attempt == 2:
                    raise
                print("  Block %d/%d fehlgeschlagen (%s), neuer Versuch..."
                      % (n + 1, len(chunks), err))
                time.sleep(1)
        sys.stdout.write("\r  Block %d/%d" % (n + 1, len(chunks)))
        sys.stdout.flush()
    print("\r  %d/%d Bloecke uebertragen." % (len(chunks), len(chunks)))


def main():
    p = argparse.ArgumentParser(
        description="Laedt ein Skript auf einen Shelly (alte Version wird geloescht)."
    )
    p.add_argument("file", nargs="?", help="Skriptdatei (.js)")
    p.add_argument("--ip", required=True, help="IP-Adresse des Shelly")
    p.add_argument("--name", help="Skriptname auf dem Shelly (Standard: Dateiname ohne .js)")
    p.add_argument("--list", action="store_true",
                   help="Nur zeigen, welche Skripte auf dem Shelly liegen")
    p.add_argument("--id", type=int,
                   help="Vorhandenes Skript mit dieser ID ersetzen "
                        "(ID und Name bleiben erhalten, statt loeschen+neu anlegen)")
    p.add_argument("--chunk-size", type=int, default=1024,
                   help="Zeichen pro PutCode-Aufruf (Standard 1024)")
    p.add_argument("--no-start", action="store_true",
                   help="Skript nur hochladen, nicht starten")
    p.add_argument("--no-enable", action="store_true",
                   help="Autostart nach Reboot nicht aktivieren")
    p.add_argument("--dry-run", action="store_true",
                   help="Nur zeigen, was passieren wuerde")
    args = p.parse_args()

    if args.list:
        try:
            list_scripts(args.ip)
        except RpcError as err:
            print("Fehler: %s" % err, file=sys.stderr)
            return 1
        return 0

    if not args.file:
        print("Fehler: Keine Skriptdatei angegeben.", file=sys.stderr)
        return 1
    if not os.path.isfile(args.file):
        print("Fehler: Datei nicht gefunden: %s" % args.file, file=sys.stderr)
        return 1

    with open(args.file, "r", encoding="utf-8", newline="") as fh:
        code = fh.read()

    name = args.name or os.path.splitext(os.path.basename(args.file))[0]
    if len(name) > 20:
        print("Hinweis: Name '%s' wird auf 20 Zeichen gekuerzt." % name)
        name = name[:20]

    print("Shelly     : %s" % args.ip)
    print("Datei      : %s (%d Zeichen)" % (args.file, len(code)))
    print("Skriptname : %s" % name)
    print("-" * 40)

    try:
        info = rpc(args.ip, "Shelly.GetDeviceInfo")
        print("Geraet     : %s (%s, fw %s)"
              % (info.get("name") or info.get("id"), info.get("model"), info.get("fw_id")))

        if args.id is not None:
            # Variante A: vorhandenes Skript in place ersetzen, ID bleibt.
            existing = None
            for s in rpc(args.ip, "Script.List").get("scripts", []):
                if s.get("id") == args.id:
                    existing = s
            if existing is None:
                print("Fehler: Kein Skript mit id=%s auf dem Shelly. "
                      "Mit --list nachsehen." % args.id, file=sys.stderr)
                return 1
            print("Ersetze Skript id=%s (name=%s), ID bleibt erhalten."
                  % (args.id, existing.get("name")))
            if args.dry_run:
                print("[DRY-RUN] wuerde gestoppt und ueberschrieben werden. Ende.")
                return 0
            if existing.get("running"):
                rpc(args.ip, "Script.Stop", {"id": args.id})
                print("  gestoppt")
            sid = args.id
        else:
            # Variante B: gleichnamiges Skript loeschen, neu anlegen.
            delete_old(args.ip, name, args.dry_run)

            if args.dry_run:
                print("[DRY-RUN] wuerde Skript anlegen und hochladen. Ende.")
                return 0

            sid = rpc(args.ip, "Script.Create", {"name": name})["id"]
            print("Neues Skript angelegt: id=%s" % sid)

        put_code(args.ip, sid, code, args.chunk_size, args.dry_run)

        if not args.no_enable:
            rpc(args.ip, "Script.SetConfig", {"id": sid, "config": {"enable": True}})
            print("Autostart aktiviert.")
        if not args.no_start:
            rpc(args.ip, "Script.Start", {"id": sid})
            time.sleep(1.5)
            status = rpc(args.ip, "Script.GetStatus", {"id": sid})
            print("Status: running=%s" % status.get("running"))
            if not status.get("running"):
                print("Warnung: Skript laeuft nicht - Logs im Shelly-Webinterface pruefen.")
                return 2
        print("-" * 40)
        print("Fertig.")
    except RpcError as err:
        print("Fehler: %s" % err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())