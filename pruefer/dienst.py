"""SysML-v2-Prüfdienst: führt Modelltext im Jupyter-Kernel der OMG-Pilotimplementierung aus (Parser und Namensauflösung)
und meldet jede Zeile „ERROR…“. Ein Kernel für alle Prüfungen; jeder Text bekommt ein eigenes Wurzelpaket.

    POST /pruefen  {"text": "..."}  ->  {"ok": bool, "meldungen": [...], "dauer_s": float, "kernel": "..."}
    python dienst.py datei.sysml …   (Prüfung von Dateien ohne Server)
"""
import itertools
import json
import queue
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jupyter_client.manager import start_new_kernel

_sperre, _zaehler = threading.Lock(), itertools.count(1)
km, kc = start_new_kernel(kernel_name="sysml")
try:
    KERNEL = subprocess.run(["micromamba", "list", "-n", "base", "jupyter-sysml-kernel", "--json"], capture_output=True,
                            text=True).stdout
    KERNEL = "jupyter-sysml-kernel " + json.loads(KERNEL)[0]["version"]
except Exception:  # noqa: BLE001 - Version ist nur Zusatzinformation
    KERNEL = "jupyter-sysml-kernel (Version unbekannt)"


def pruefen(text: str) -> dict:
    with _sperre:
        n = next(_zaehler)
        # eigenes Wurzelpaket je Prüfung, damit frühere Prüfungen im Kernel nicht mitzählen
        code = re.sub(r"^package\s+(\w+)\s*\{", lambda m: f"package {m.group(1)}_pruefung{n} {{", text, count=1, flags=re.M)
        t = time.perf_counter()
        msg_id = kc.execute(code)
        meldungen, ergebnis = [], ""
        while True:
            try:
                m = kc.get_iopub_msg(timeout=180)
            except queue.Empty:
                meldungen.append("Zeitüberschreitung im Kernel")
                break
            if m["parent_header"].get("msg_id") != msg_id:
                continue
            art, inhalt = m["msg_type"], m["content"]
            if art == "status" and inhalt["execution_state"] == "idle":
                break
            if art == "stream":
                meldungen += [z for z in inhalt["text"].splitlines() if z.strip()]
            elif art == "execute_result":
                ergebnis = inhalt["data"].get("text/plain", "")
            elif art == "error":
                meldungen.append(f"{inhalt.get('ename')}: {inhalt.get('evalue')}")
        fehler = [z for z in meldungen if z.startswith("ERROR") or "Zeitüberschreitung" in z or ":" in z and "Error" in z]
        return {"ok": not fehler and ergebnis.startswith("Package"), "meldungen": meldungen,
                "ergebnis": ergebnis.strip()[:200], "dauer_s": round(time.perf_counter() - t, 2), "kernel": KERNEL}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path != "/pruefen":
            self.send_error(404)
            return
        laenge = int(self.headers.get("Content-Length", 0))
        antwort = json.dumps(pruefen(json.loads(self.rfile.read(laenge))["text"]), ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(antwort)))
        self.end_headers()
        self.wfile.write(antwort)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for datei in sys.argv[1:]:
            print(datei, json.dumps(pruefen(open(datei, encoding="utf-8").read()), ensure_ascii=False))
    else:
        print(f"Prüfdienst bereit ({KERNEL})", flush=True)
        ThreadingHTTPServer(("0.0.0.0", 8100), Handler).serve_forever()
