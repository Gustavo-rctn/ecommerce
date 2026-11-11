import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ErroMercadoPago(Exception):
    def __init__(self, mensagem: str, status_http: int = 502):
        super().__init__(mensagem)
        self.status_http = status_http


def obter_chave_publica() -> str:
    return os.environ.get("MERCADOPAGO_PUBLIC_KEY", "").strip()


def _obter_token_acesso() -> str:
    token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
    if not token:
        raise ErroMercadoPago(
            "Mercado Pago não configurado. Defina MERCADOPAGO_ACCESS_TOKEN no ambiente do servidor.",
            503,
        )
    return token


def _requisicao(path: str, metodo: str = "GET", dados: dict | None = None, chave_idempotencia: str | None = None) -> dict:
    token = _obter_token_acesso()
    corpo = json.dumps(dados).encode("utf-8") if dados is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if corpo is not None:
        headers["Content-Type"] = "application/json"
    if chave_idempotencia:
        headers["X-Idempotency-Key"] = chave_idempotencia

    requisicao = Request(
        f"https://api.mercadopago.com{path}",
        data=corpo,
        headers=headers,
        method=metodo,
    )

    try:
        with urlopen(requisicao, timeout=25) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except HTTPError as erro:
        try:
            detalhe = json.loads(erro.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            detalhe = {}
        mensagem = detalhe.get("message") or detalhe.get("error") or "O Mercado Pago recusou a solicitação."
        raise ErroMercadoPago(str(mensagem), erro.code) from erro
    except URLError as erro:
        raise ErroMercadoPago("Não foi possível conectar ao Mercado Pago. Tente novamente.") from erro
    except (TimeoutError, json.JSONDecodeError) as erro:
        raise ErroMercadoPago("O Mercado Pago não retornou uma resposta válida. Tente novamente.") from erro


def criar_pagamento(dados: dict, chave_idempotencia: str) -> dict:
    if not chave_idempotencia:
        raise ErroMercadoPago("Identificador de checkout ausente.", 400)
    return _requisicao("/v1/payments", "POST", dados, chave_idempotencia)


def consultar_pagamento(pagamento_id: str) -> dict:
    return _requisicao(f"/v1/payments/{pagamento_id}")
