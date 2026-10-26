"""LechuJob — servidor local.

Sirve la interfaz en http://localhost:8765 y ejecuta los agentes de Claude Code
(`claude -p /buscar-ofertas`, `/seguimiento`) en segundo plano, mostrando su avance.
Solo usa la librería estándar de Python.
"""

import json
import re
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
APP_DIR = Path(__file__).resolve().parent
WORKDIR = APP_DIR  # ahí viven .claude/agents y .claude/commands
DATA = APP_DIR / "data"
STATIC = APP_DIR / "static"
CONFIG = APP_DIR / "config" / "candidato.yaml"


def sheet_url():
    """URL del Sheet a partir de `google_sheet_id` en config/candidato.yaml (archivo local, no versionado)."""
    try:
        m = re.search(r"^google_sheet_id:\s*(\S+)", CONFIG.read_text(encoding="utf-8"), re.M)
    except OSError:
        m = None
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/edit" if m else None

CLAUDE = shutil.which("claude") or "/opt/homebrew/bin/claude"

COMMANDS = {
    "buscar": "/buscar-ofertas",
    "seguimiento": "/seguimiento",
}

ALLOWED_TOOLS = [
    "Task", "Agent", "Read", "WebFetch", "WebSearch",
    "Edit(./data/**)",  # las reglas Edit cubren también Write
    "mcp__claude_ai_Gmail__search_threads",
    "mcp__claude_ai_Gmail__get_thread",
    "mcp__claude_ai_Google_Sheets__get_values",
    "mcp__claude_ai_Google_Sheets__update_values",
]

# Estado de la corrida en curso (una a la vez).
run_lock = threading.Lock()
run = {"running": False, "tipo": None, "inicio": None, "fin": None, "lineas": [], "resultado": None, "error": None}


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def describe_event(ev):
    """Convierte un evento stream-json de Claude Code en una línea legible (o None)."""
    t = ev.get("type")
    if t == "assistant":
        out = []
        sub = " ↳ " if ev.get("parent_tool_use_id") else ""
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text", "").strip():
                out.append(f"{sub}💬 {block['text'].strip()}")
            elif block.get("type") == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})
                if name in ("Task", "Agent"):
                    out.append(f"🦉 Agente {inp.get('subagent_type', '')}: {inp.get('description', '')}")
                else:
                    short = name.replace("mcp__claude_ai_", "").replace("__", " · ")
                    detail = inp.get("query") or inp.get("range") or inp.get("url") or inp.get("file_path") or ""
                    out.append(f"{sub}🔧 {short} {str(detail)[:90]}")
        return "\n".join(out) or None
    if t == "result":
        return None
    return None


def run_claude(tipo):
    log_path = DATA / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}-{tipo}.log"
    cmd = [CLAUDE, "-p", COMMANDS[tipo], "--output-format", "stream-json", "--verbose",
           "--allowedTools", ",".join(ALLOWED_TOOLS)]
    try:
        proc = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        with log_path.open("w", encoding="utf-8") as log:
            for raw in proc.stdout:
                log.write(raw)
                try:
                    ev = json.loads(raw)
                except ValueError:
                    line = raw.strip() or None
                    ev = None
                else:
                    line = describe_event(ev)
                    if ev.get("type") == "result":
                        with run_lock:
                            run["resultado"] = ev.get("result")
                            if ev.get("is_error"):
                                run["error"] = ev.get("result") or "La corrida terminó con error."
                if line:
                    with run_lock:
                        run["lineas"].append(line)
                        run["lineas"] = run["lineas"][-300:]
        code = proc.wait()
        if code != 0:
            with run_lock:
                run["error"] = run["error"] or f"claude terminó con código {code}. Log: {log_path.name}"
    except Exception as exc:  # noqa: BLE001 — cualquier fallo se muestra en la UI
        with run_lock:
            run["error"] = str(exc)
    finally:
        with run_lock:
            run["running"] = False
            run["fin"] = datetime.now().isoformat(timespec="seconds")


def start_run(tipo):
    with run_lock:
        if run["running"]:
            return False
        run.update(running=True, tipo=tipo, inicio=datetime.now().isoformat(timespec="seconds"),
                   fin=None, lineas=[], resultado=None, error=None)
    threading.Thread(target=run_claude, args=(tipo,), daemon=True).start()
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, ctype):
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_file(STATIC / "index.html", "text/html; charset=utf-8")
        elif self.path == "/logo.svg":
            self.send_file(STATIC / "logo.svg", "image/svg+xml")
        elif self.path == "/api/state":
            with run_lock:
                run_copy = dict(run, lineas=list(run["lineas"]))
            self.send_json({
                "reporte": read_json(DATA / "reporte.json", None),
                "estado": read_json(DATA / "estado.json", None),
                "seleccion": read_json(DATA / "seleccion.json", {"ids": []}),
                "run": run_copy,
                "sheet_url": sheet_url(),
            })
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/run":
            tipo = self.read_body().get("tipo")
            if tipo not in COMMANDS:
                self.send_json({"ok": False, "error": "Acción desconocida"}, 400)
            elif not start_run(tipo):
                self.send_json({"ok": False, "error": "Ya hay una corrida en curso"}, 409)
            else:
                self.send_json({"ok": True})
        elif self.path == "/api/seleccion":
            ids = [str(i) for i in self.read_body().get("ids", [])]
            data = {"ids": ids, "guardado": datetime.now().isoformat(timespec="seconds")}
            (DATA / "seleccion.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_json({"ok": True, **data})
        else:
            self.send_error(404)


def main():
    (DATA / "runs").mkdir(parents=True, exist_ok=True)
    procesados = DATA / "procesados.json"
    if not procesados.exists():
        procesados.write_text('{"threads": [], "ofertas": []}', encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"LechuJob corriendo en {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
