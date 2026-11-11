import logging
import os
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main

_schema_lock = threading.Lock()
_schema_ready = False


class handler(main.LojaRequestHandler):
    def _prepare_api_request(self):
        partes = urlsplit(self.path)
        rota = parse_qs(partes.query).get("route", [""])[0]
        if rota.startswith("/api/") and ".." not in rota.split("/"):
            self.path = rota

        if not urlsplit(self.path).path.startswith("/api/"):
            return True

        if not os.environ.get("DATABASE_URL", "").strip():
            self._send_json(
                503,
                {
                    "ok": False,
                    "message": "Configure DATABASE_URL com a conexão do Neon nas variáveis do projeto Vercel.",
                },
            )
            return False

        global _schema_ready
        if not _schema_ready:
            with _schema_lock:
                if not _schema_ready:
                    try:
                        main.inicializar_todas_as_tabelas()
                    except Exception:
                        logging.exception("Não foi possível inicializar o banco Neon.")
                        self._send_json(
                            503,
                            {
                                "ok": False,
                                "message": "Banco Neon indisponível. Confira a variável DATABASE_URL no Vercel.",
                            },
                        )
                        return False
                    _schema_ready = True
        return True

    def do_GET(self):
        if self._prepare_api_request():
            super().do_GET()

    def do_POST(self):
        if self._prepare_api_request():
            super().do_POST()
