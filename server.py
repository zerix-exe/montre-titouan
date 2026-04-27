#!/usr/bin/env python3
"""
Serveur local pour le vote de montre de Titouan.
Lance avec : python server.py
Puis ouvre http://localhost:8080 dans ton navigateur.
Les votes sont sauvegardés dans votes.json dans le dossier MONTRES.
"""

import http.server
import json
import os
import pathlib
from datetime import datetime

# Dossier du script = dossier MONTRES
BASE_DIR = pathlib.Path(__file__).parent
VOTES_FILE = BASE_DIR / "votes.json"
HTML_FILE  = BASE_DIR / "index.html"
PORT = int(os.environ.get("PORT", 8080))


def load_votes():
    if VOTES_FILE.exists():
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"votes": []}


def save_votes(data):
    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Log propre dans le terminal
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(HTML_FILE, "text/html; charset=utf-8")
        elif self.path == "/votes":
            data = load_votes()
            self._json_response(200, data)
        elif self.path.startswith("/images/"):
            from urllib.parse import unquote
            fname = unquote(self.path[len("/images/"):])
            fpath = BASE_DIR / fname
            if fpath.exists() and fpath.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                self._serve_file(fpath, "image/png")
            else:
                self._json_response(404, {"error": "not found"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/vote":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                vote = json.loads(body)
            except Exception:
                self._json_response(400, {"error": "invalid json"})
                return

            # Validation minimale
            if not vote.get("name") or vote.get("watch") is None:
                self._json_response(400, {"error": "missing fields"})
                return

            data = load_votes()

            # Anti-doublon par prénom (insensible à la casse)
            existing = [v for v in data["votes"]
                        if v["name"].lower() == vote["name"].strip().lower()]
            if existing:
                self._json_response(409, {"error": "already_voted"})
                return

            data["votes"].append({
                "name":     vote["name"].strip(),
                "relation": vote.get("relation", "—").strip() or "—",
                "watch":    int(vote["watch"]),
                "comment":  vote.get("comment", "").strip(),
                "date":     datetime.now().strftime("%d/%m/%Y %H:%M"),
            })
            save_votes(data)
            print(f"  ✓ Vote enregistré : {vote['name']} → montre #{vote['watch']}")
            self._json_response(200, {"ok": True, "total": len(data["votes"])})

        elif self.path == "/reset":
            # Réinitialiser les votes (utile pour les tests)
            save_votes({"votes": []})
            self._json_response(200, {"ok": True})
        else:
            self._json_response(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._json_response(404, {"error": "file not found"})

    def _json_response(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║   🕐 Serveur Vote Montre — Titouan       ║
╠══════════════════════════════════════════╣
║  Ouvre dans ton navigateur :             ║
║  → http://localhost:{PORT}                 ║
║                                          ║
║  Votes sauvegardés dans : votes.json     ║
║  Arrêt : Ctrl+C                          ║
╚══════════════════════════════════════════╝
""")
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Serveur arrêté. À bientôt !")
