import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import sys
import threading
import uuid
from decimal import Decimal
from http.cookies import CookieError, SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from back_end.fake import gerar_produtos_falsos
from back_end import mercado_pago

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETO = DIRETORIO_ATUAL
PASTA_DATABASE = os.path.join(RAIZ_PROJETO, "database")
CAMINHO_BANCO = os.path.join(PASTA_DATABASE, "loja.db")
PASTA_FRONTEND = RAIZ_PROJETO
PASTA_FRONTEND_LEGADO = os.path.join(RAIZ_PROJETO, "front_end", "HTML")
CATALOGO_WEB = {
    1: {
        "nome": "Teclado Gamer Mechanical",
        "resumo": "Teclado mecânico",
        "preco": Decimal("150.00"),
        "estoque": 10,
        "categoria": "SETUP",
        "descricao": "Precisão e resposta tátil para acompanhar cada ideia. Um teclado mecânico feito para longas sessões de criação e jogo.",
        "imagem": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
    },
    2: {
        "nome": "Mouse Pad Extra Grande",
        "resumo": "Superfície ampla",
        "preco": Decimal("40.00"),
        "estoque": 5,
        "categoria": "SETUP",
        "descricao": "Mais espaço para movimentos precisos e uma mesa com visual organizado. Superfície ampla para o seu ritmo.",
        "imagem": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=80",
    },
    3: {
        "nome": "Headset Surround 7.1",
        "resumo": "Áudio imersivo",
        "preco": Decimal("220.00"),
        "estoque": 8,
        "categoria": "ÁUDIO",
        "descricao": "Som envolvente e confortável para partidas, chamadas e playlists. Foco no que você precisa ouvir.",
        "imagem": "https://images.unsplash.com/photo-1599669454699-248893623440?auto=format&fit=crop&w=900&q=80",
    },
    4: {
        "nome": "Monitor 144Hz Full HD",
        "resumo": "Imagem fluida",
        "preco": Decimal("950.00"),
        "estoque": 3,
        "categoria": "IMAGEM",
        "descricao": "Mais fluidez para acompanhar cada movimento. Uma tela Full HD de 144Hz para trabalho e entretenimento.",
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
}
CATALOGO_WEB.update(
    gerar_produtos_falsos(quantidade=8, seed=42, primeiro_id=max(CATALOGO_WEB) + 1)
)

TEMAS_DISPONIVEIS = {"light", "dark", "purple", "night-owl"}
ITERACOES_HASH_SENHA = 310_000
TEMPO_SESSAO_SEGUNDOS = 30 * 24 * 60 * 60
_SCHEMA_INICIALIZADO = False
_SCHEMA_LOCK = threading.Lock()


class _CursorPostgres:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query, parametros=()):
        query = query.replace("?", "%s")
        insercao = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z_0-9]*)\b", query, re.IGNORECASE)
        if insercao and insercao.group(1).lower() in {"usuarios", "pedidos", "carrinho", "pagamentos"} and "RETURNING" not in query.upper():
            self._cursor.execute(f"{query.rstrip().rstrip(';')} RETURNING id", parametros)
            linha = self._cursor.fetchone()
            self.lastrowid = linha[0] if linha else None
        else:
            self._cursor.execute(query, parametros)
            self.lastrowid = None
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class _ConexaoPostgres:
    def __init__(self, conexao):
        self._conexao = conexao

    def cursor(self):
        return _CursorPostgres(self._conexao.cursor())

    def execute(self, query, parametros=()):
        return self.cursor().execute(query, parametros)

    def commit(self):
        self._conexao.commit()

    def rollback(self):
        self._conexao.rollback()

    def close(self):
        self._conexao.close()


def _usar_postgres() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


def conectar_banco():
    if not _usar_postgres():
        os.makedirs(PASTA_DATABASE, exist_ok=True)
        return sqlite3.connect(CAMINHO_BANCO)

    try:
        import psycopg
    except ImportError as erro:
        raise RuntimeError("Instale as dependências do projeto para conectar ao Neon.") from erro
    return _ConexaoPostgres(psycopg.connect(os.environ["DATABASE_URL"].strip()))


def _erro_integridade_banco(erro: Exception) -> bool:
    return isinstance(erro, sqlite3.IntegrityError) or getattr(erro, "sqlstate", None) in {
        "23502", "23503", "23505", "23514",
    }


def inicializar_todas_as_tabelas():
    if _usar_postgres():
        conexao = conectar_banco()
        try:
            cursor = conexao.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    foto_perfil TEXT NOT NULL DEFAULT '',
                    tema TEXT NOT NULL DEFAULT 'dark'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    id BIGSERIAL PRIMARY KEY,
                    login_id BIGINT NOT NULL REFERENCES usuarios(id),
                    total NUMERIC(10, 2) NOT NULL,
                    data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(255) NOT NULL,
                    checkout_key TEXT UNIQUE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS carrinho (
                    id BIGSERIAL PRIMARY KEY,
                    produtos_id BIGINT NOT NULL,
                    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
                    quantidade INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pagamentos (
                    id BIGSERIAL PRIMARY KEY,
                    email_usuario TEXT NOT NULL,
                    valor NUMERIC(10, 2) NOT NULL,
                    forma_pagamento TEXT NOT NULL,
                    status TEXT NOT NULL,
                    codigo_transacao TEXT UNIQUE NOT NULL,
                    data_transacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    pedido_id BIGINT REFERENCES pedidos(id),
                    status_provedor TEXT,
                    boleto_url TEXT,
                    boleto_codigo TEXT,
                    pix_codigo TEXT,
                    pix_qr_base64 TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessoes (
                    token_hash TEXT PRIMARY KEY,
                    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    expira_em TIMESTAMPTZ NOT NULL
                )
            """)
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto_perfil TEXT NOT NULL DEFAULT ''")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tema TEXT NOT NULL DEFAULT 'dark'")
            cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS checkout_key TEXT")
            for coluna in ("pedido_id BIGINT", "status_provedor TEXT", "boleto_url TEXT", "boleto_codigo TEXT", "pix_codigo TEXT", "pix_qr_base64 TEXT"):
                cursor.execute(f"ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS {coluna}")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pedidos_checkout_key ON pedidos(checkout_key)")
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()
        return

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(255) NOT NULL,
            checkout_key TEXT UNIQUE,
            FOREIGN KEY (login_id) REFERENCES usuarios (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Carrinho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produtos_id INTEGER NOT NULL,
            pedido_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES Pedidos (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_usuario TEXT NOT NULL,
            valor DECIMAL(10, 2) NOT NULL,
            forma_pagamento TEXT NOT NULL,
            status TEXT NOT NULL,
            codigo_transacao TEXT UNIQUE NOT NULL,
            data_transacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pedido_id INTEGER,
            status_provedor TEXT,
            boleto_url TEXT,
            boleto_codigo TEXT,
            pix_codigo TEXT,
            pix_qr_base64 TEXT,
            FOREIGN KEY (pedido_id) REFERENCES Pedidos (id)
        )
    """)

    colunas_usuarios = {linha[1] for linha in cursor.execute("PRAGMA table_info(usuarios)")}
    for coluna, definicao in {
        "foto_perfil": "TEXT NOT NULL DEFAULT ''",
        "tema": "TEXT NOT NULL DEFAULT 'dark'",
    }.items():
        if coluna not in colunas_usuarios:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {definicao}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            token_hash TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            expira_em TIMESTAMP NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
        )
    """)

    colunas_pedidos = {linha[1] for linha in cursor.execute("PRAGMA table_info(Pedidos)")}
    if "checkout_key" not in colunas_pedidos:
        cursor.execute("ALTER TABLE Pedidos ADD COLUMN checkout_key TEXT")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pedidos_checkout_key ON Pedidos(checkout_key)")

    colunas_pagamentos = {linha[1] for linha in cursor.execute("PRAGMA table_info(pagamentos)")}
    for coluna, definicao in {
        "pedido_id": "INTEGER",
        "status_provedor": "TEXT",
        "boleto_url": "TEXT",
        "boleto_codigo": "TEXT",
        "pix_codigo": "TEXT",
        "pix_qr_base64": "TEXT",
    }.items():
        if coluna not in colunas_pagamentos:
            cursor.execute(f"ALTER TABLE pagamentos ADD COLUMN {coluna} {definicao}")

    conexao.commit()
    conexao.close()


def usuario_existe(email: str) -> bool:
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado is not None


def _criar_hash_senha(senha: str) -> str:
    sal = secrets.token_hex(16)
    derivacao = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES_HASH_SENHA
    )
    return f"pbkdf2_sha256${ITERACOES_HASH_SENHA}${sal}${derivacao.hex()}"


def _verificar_senha(senha: str, hash_armazenado: str) -> tuple[bool, bool]:
    partes = hash_armazenado.split("$")
    if len(partes) == 4 and partes[0] == "pbkdf2_sha256":
        try:
            iteracoes = int(partes[1])
            if not 1 <= iteracoes <= 1_000_000:
                return False, False
            derivacao = hashlib.pbkdf2_hmac(
                "sha256", senha.encode("utf-8"), bytes.fromhex(partes[2]), iteracoes
            )
        except (ValueError, OverflowError):
            return False, False
        return hmac.compare_digest(derivacao.hex(), partes[3]), False

    return hmac.compare_digest(senha, hash_armazenado), True


def _dados_publicos_usuario(linha: tuple) -> dict:
    return {
        "id": linha[0],
        "name": linha[1],
        "email": linha[2],
        "photo": linha[3] or "",
        "theme": linha[4] if linha[4] in TEMAS_DISPONIVEIS else "dark",
    }


def criar_conta(nome: str, email: str, senha: str) -> tuple[dict, str]:
    if not isinstance(nome, str) or not isinstance(email, str) or not isinstance(senha, str):
        raise ValueError("Informe nome, e-mail e senha válidos.")
    nome = nome.strip()
    email = email.strip().lower()
    if not nome or len(nome) > 100 or not re.fullmatch(r"[A-Za-zÀ-ÿ\s]+", nome):
        raise ValueError("Informe seu nome completo usando apenas letras e espaços.")
    if len(email) > 100 or not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("O e-mail informado é inválido.")
    if not 6 <= len(senha) <= 20 or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)", senha):
        raise ValueError("A senha deve ter entre 6 e 20 caracteres e conter pelo menos uma letra e um número.")

    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
            (nome, email, _criar_hash_senha(senha)),
        )
        usuario_id = cursor.lastrowid
        token = _criar_sessao(cursor, usuario_id)
        conexao.commit()
        linha = cursor.execute(
            "SELECT id, nome, email, foto_perfil, tema FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        return _dados_publicos_usuario(linha), token
    except Exception as erro:
        conexao.rollback()
        if _erro_integridade_banco(erro):
            raise ValueError("Este e-mail já está cadastrado. Entre na sua conta.") from erro
        raise
    finally:
        conexao.close()


def _criar_sessao(cursor: sqlite3.Cursor, usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    if _usar_postgres():
        cursor.execute(
            "INSERT INTO sessoes (token_hash, usuario_id, expira_em) "
            "VALUES (?, ?, CURRENT_TIMESTAMP + INTERVAL '30 days')",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(), usuario_id),
        )
    else:
        cursor.execute(
            "INSERT INTO sessoes (token_hash, usuario_id, expira_em) "
            "VALUES (?, ?, datetime('now', '+30 days'))",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(), usuario_id),
        )
    return token


def autenticar_usuario(email: str, senha: str) -> tuple[dict, str]:
    email = email.strip().lower()
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        linha = cursor.execute(
            "SELECT id, nome, email, senha, foto_perfil, tema FROM usuarios WHERE email = ?",
            (email,),
        ).fetchone()
        if not linha:
            raise ValueError("E-mail ou senha incorretos.")

        senha_valida, senha_legada = _verificar_senha(senha, linha[3])
        if not senha_valida:
            raise ValueError("E-mail ou senha incorretos.")
        if senha_legada:
            cursor.execute(
                "UPDATE usuarios SET senha = ? WHERE id = ?",
                (_criar_hash_senha(senha), linha[0]),
            )
        token = _criar_sessao(cursor, linha[0])
        conexao.commit()
        return _dados_publicos_usuario((linha[0], linha[1], linha[2], linha[4], linha[5])), token
    finally:
        conexao.close()


def obter_usuario_da_sessao(token: str) -> dict | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conexao = conectar_banco()
    try:
        linha = conexao.execute(
            "SELECT u.id, u.nome, u.email, u.foto_perfil, u.tema "
            "FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
            "WHERE s.token_hash = ? AND s.expira_em > CURRENT_TIMESTAMP",
            (token_hash,),
        ).fetchone()
        return _dados_publicos_usuario(linha) if linha else None
    finally:
        conexao.close()


def atualizar_perfil(usuario_id: int, alteracoes: dict) -> dict:
    atualizacoes = {}
    if "name" in alteracoes:
        nome = alteracoes["name"]
        if not isinstance(nome, str):
            raise ValueError("O nome informado é inválido.")
        nome = nome.strip()
        if not nome or len(nome) > 100 or not re.fullmatch(r"[A-Za-zÀ-ÿ\s]+", nome):
            raise ValueError("Informe seu nome completo usando apenas letras e espaços.")
        atualizacoes["nome"] = nome
    if "email" in alteracoes:
        email = alteracoes["email"]
        if not isinstance(email, str):
            raise ValueError("O e-mail informado é inválido.")
        email = email.strip().lower()
        if len(email) > 100 or not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("O e-mail informado é inválido.")
        atualizacoes["email"] = email
    if "theme" in alteracoes:
        tema = alteracoes["theme"]
        if not isinstance(tema, str) or tema not in TEMAS_DISPONIVEIS:
            raise ValueError("O tema selecionado é inválido.")
        atualizacoes["tema"] = tema
    if "photo" in alteracoes:
        foto = alteracoes["photo"]
        if not isinstance(foto, str) or len(foto) > 2_800_000:
            raise ValueError("A foto precisa ser uma imagem válida de até 2 MB.")
        if foto and not re.fullmatch(
            r"data:image/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/]+={0,2}", foto
        ):
            raise ValueError("A foto precisa ser PNG, JPEG, WebP ou GIF.")
        atualizacoes["foto_perfil"] = foto
    if not atualizacoes:
        raise ValueError("Nenhuma alteração de perfil foi informada.")

    colunas = ", ".join(f"{coluna} = ?" for coluna in atualizacoes)
    valores = [*atualizacoes.values(), usuario_id]
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE usuarios SET {colunas} WHERE id = ?", valores)
        if cursor.rowcount == 0:
            raise ValueError("Não foi possível encontrar essa conta.")
        linha = cursor.execute(
            "SELECT id, nome, email, foto_perfil, tema FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        conexao.commit()
        return _dados_publicos_usuario(linha)
    except Exception as erro:
        conexao.rollback()
        if _erro_integridade_banco(erro):
            raise ValueError("Este e-mail já está sendo usado por outra conta.") from erro
        raise
    finally:
        conexao.close()


def cadastrar_usuario(nome: str, sobrenome: str, email: str, senha: str) -> dict:
    nome = nome.strip()
    sobrenome = sobrenome.strip()
    email = email.strip().lower()

    if not nome or not sobrenome or not email or not senha:
        raise ValueError("Todos os campos são obrigatórios.")
    if len(nome) < 3 or len(nome) > 50 or not re.match(r"^[A-Za-zÀ-ÿ\s]+$", nome):
        raise ValueError("O nome deve ter entre 3 e 50 caracteres (apenas letras).")
    if len(sobrenome) < 3 or len(sobrenome) > 50 or not re.match(r"^[A-Za-zÀ-ÿ\s]+$", sobrenome):
        raise ValueError("O sobrenome deve ter entre 3 e 50 caracteres (apenas letras).")
    if len(email) > 100 or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("O e-mail informado é inválido.")
    if len(senha) < 6 or len(senha) > 20 or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)", senha):
        raise ValueError("A senha deve ter entre 6 e 20 caracteres e conter pelo menos uma letra e um número.")

    if usuario_existe(email):
        raise ValueError("Este e-mail já está cadastrado no sistema.")

    nome_completo = f"{nome} {sobrenome}"

    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome_completo, email, _criar_hash_senha(senha))
    )
    usuario_id = cursor.lastrowid
    conexao.commit()
    conexao.close()

    return {"id": usuario_id, "nome": nome_completo, "email": email}


def criar_carrinho() -> dict:
    return {"itens": {}, "cupom": None}


def adicionar_item(carrinho: dict, produto_id: int, nome: str, preco: Decimal, quantidade: int, estoque: dict) -> dict:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    qtd_atual = carrinho["itens"].get(produto_id, {}).get("quantidade", 0)
    qtd_total = qtd_atual + quantidade

    if produto_id not in estoque or qtd_total > estoque[produto_id]["estoque"]:
        raise ValueError(f"Estoque insuficiente! Disponível: {estoque[produto_id]['estoque']} un.")

    carrinho["itens"][produto_id] = {
        "nome": nome,
        "preco": preco,
        "quantidade": qtd_total
    }
    return carrinho


def calcular_frete_simulado(cep: str) -> Decimal:
    cep_limpo = cep.strip().replace("-", "")
    if not re.match(r"^\d{8}$", cep_limpo):
        raise ValueError("CEP inválido! Digite exatamente 8 números.")
    return Decimal("15.00") if cep_limpo.startswith(("0", "1")) else Decimal("25.00")


def aplicar_cupom(carrinho: dict, cupom_nome: str) -> dict:
    cupom_limpo = cupom_nome.strip().upper()
    cupons_validos = {
        "DESCONTO10": Decimal("0.10"),
        "DESCONTO20": Decimal("0.20")
    }

    if cupom_limpo not in cupons_validos:
        raise ValueError("Cupom inválido ou expirado.")

    carrinho["cupom"] = {"nome": cupom_limpo, "desconto": cupons_validos[cupom_limpo]}
    return carrinho


def calcular_total_carrinho(carrinho: dict, frete: Decimal) -> dict:
    subtotal = sum(item["preco"] * item["quantidade"] for item in carrinho["itens"].values())
    desconto = (subtotal * carrinho["cupom"]["desconto"]) if carrinho["cupom"] else Decimal("0.00")
    total = subtotal - desconto + frete

    return {
        "subtotal": subtotal,
        "desconto": desconto,
        "frete": frete,
        "total": total
    }


def fechar_pedido(cliente_id: int, carrinho: dict, resumo: dict, estoque: dict) -> dict:
    for produto_id, item in carrinho["itens"].items():
        estoque[produto_id]["estoque"] -= item["quantidade"]

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO Pedidos (login_id, total, status) VALUES (?, ?, ?)
    """, (cliente_id, float(resumo["total"]), "AGUARDANDO_PAGAMENTO"))
    pedido_id = cursor.lastrowid

    for produto_id, item in carrinho["itens"].items():
        cursor.execute("""
            INSERT INTO Carrinho (produtos_id, pedido_id, quantidade) VALUES (?, ?, ?)
        """, (produto_id, pedido_id, item["quantidade"]))

    conexao.commit()
    conexao.close()

    return {
        "pedido_id": pedido_id,
        "cliente_id": cliente_id,
        "total": resumo["total"],
        "status": "AGUARDANDO_PAGAMENTO"
    }


def processar_pagamento(email: str, forma: str, valor: float, **dados) -> dict:
    raise ValueError("Pagamentos simulados foram desativados. Use o checkout web com Mercado Pago.")


def obter_ou_criar_usuario(email: str, nome: str) -> int:
    email = email.strip().lower()
    if not email:
        raise ValueError("E-mail obrigatório.")

    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        usuario = cursor.fetchone()
        if usuario:
            return usuario[0]

        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
            (nome.strip(), email, uuid.uuid4().hex),
        )
        conexao.commit()
        return cursor.lastrowid
    finally:
        conexao.close()


def montar_carrinho_web(itens: list) -> dict:
    carrinho = {"itens": {}}
    if not isinstance(itens, list) or not itens:
        raise ValueError("Seu carrinho está vazio.")

    for item in itens:
        if not isinstance(item, dict):
            raise ValueError("Há um item inválido no carrinho.")
        produto_id_original = item.get("id")
        quantidade_original = item.get("quantity", item.get("quantidade", 1))
        if (
            isinstance(produto_id_original, bool)
            or isinstance(quantidade_original, bool)
            or isinstance(produto_id_original, float) and not produto_id_original.is_integer()
            or isinstance(quantidade_original, float) and not quantidade_original.is_integer()
        ):
            raise ValueError("ID do produto e quantidade devem ser números inteiros.")
        try:
            produto_id = int(produto_id_original)
            quantidade = int(quantidade_original)
        except (TypeError, ValueError, OverflowError) as erro:
            raise ValueError("ID do produto e quantidade devem ser números inteiros.") from erro

        produto = CATALOGO_WEB.get(produto_id)
        if not produto:
            raise ValueError(f"Produto {produto_id} não existe no catálogo.")
        if quantidade <= 0 or quantidade > produto["estoque"]:
            raise ValueError(f"Quantidade inválida para {produto['nome']}.")

        item_existente = carrinho["itens"].get(produto_id)
        quantidade_total = quantidade + (item_existente["quantidade"] if item_existente else 0)
        if quantidade_total > produto["estoque"]:
            raise ValueError(f"Estoque insuficiente para {produto['nome']}.")

        carrinho["itens"][produto_id] = {
            "nome": produto["nome"],
            "preco": produto["preco"],
            "quantidade": quantidade_total,
        }

    if not carrinho["itens"]:
        raise ValueError("Seu carrinho está vazio.")

    return carrinho


def _status_pagamento(status_provedor: str) -> tuple[str, str]:
    status = (status_provedor or "").lower()
    if status == "approved":
        return "Aprovado", "LIBERADO"
    if status in {"rejected"}:
        return "Rejeitado", "PAGAMENTO_RECUSADO"
    if status in {"cancelled", "refunded", "charged_back"}:
        return status.upper(), "PAGAMENTO_CANCELADO"
    return "Pendente", "AGUARDANDO_PAGAMENTO"


def _resposta_checkout(pedido_id: int, checkout_key: str, valor: float, metodo: str, pagamento: dict) -> dict:
    dados_interacao = pagamento.get("point_of_interaction", {}).get("transaction_data", {})
    detalhes_transacao = pagamento.get("transaction_details", {})
    boleto = {
        "url": detalhes_transacao.get("external_resource_url") or pagamento.get("ticket_url"),
        "codigo": pagamento.get("barcode", {}).get("content") or detalhes_transacao.get("digitable_line"),
    }
    pix = {
        "codigo": dados_interacao.get("qr_code"),
        "qr_base64": dados_interacao.get("qr_code_base64"),
        "url": dados_interacao.get("ticket_url"),
    }
    status_pagamento, status_pedido = _status_pagamento(pagamento.get("status", "pending"))
    return {
        "ok": True,
        "message": "Pagamento aprovado." if status_pedido == "LIBERADO" else "Cobrança criada; o pedido aguarda a confirmação do pagamento.",
        "order": {
            "id": pedido_id,
            "checkout_key": checkout_key,
            "status": status_pedido,
            "total": float(valor),
            "payment": metodo,
            "payment_status": status_pagamento,
            "payment_id": str(pagamento.get("id", "")),
        },
        "payment": {
            "status": status_pagamento,
            "status_detail": pagamento.get("status_detail", ""),
            "pix": pix if metodo == "PIX" else None,
            "boleto": boleto if metodo == "BOLETO" else None,
        },
    }


def _criar_checkout_demo(email: str, nome: str, checkout_key: str, carrinho: dict, total: Decimal, metodo: str) -> dict:
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT o.id, o.total, o.checkout_key, p.forma_pagamento
            FROM Pedidos o
            JOIN pagamentos p ON p.pedido_id = o.id
            WHERE o.checkout_key = ?
            """,
            (checkout_key,),
        )
        pedido_existente = cursor.fetchone()
        if pedido_existente:
            return {
                "ok": True,
                "demo": True,
                "order": {
                    "id": pedido_existente[0],
                    "checkout_key": pedido_existente[2],
                    "status": "DEMONSTRACAO",
                    "total": float(pedido_existente[1]),
                    "payment": pedido_existente[3],
                    "payment_status": "NAO_REALIZADO",
                },
                "payment": {"demo": True, "status": "NAO_REALIZADO"},
            }

        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        usuario = cursor.fetchone()
        if usuario:
            cliente_id = usuario[0]
        else:
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (nome, email, uuid.uuid4().hex),
            )
            cliente_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO Pedidos (login_id, total, status, checkout_key) VALUES (?, ?, ?, ?)",
            (cliente_id, float(total), "DEMONSTRACAO", checkout_key),
        )
        pedido_id = cursor.lastrowid
        for produto_id, item in carrinho["itens"].items():
            cursor.execute(
                "INSERT INTO Carrinho (produtos_id, pedido_id, quantidade) VALUES (?, ?, ?)",
                (produto_id, pedido_id, item["quantidade"]),
            )
        cursor.execute(
            """
            INSERT INTO pagamentos (
                email_usuario, valor, forma_pagamento, status, codigo_transacao,
                pedido_id, status_provedor
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                float(total),
                metodo,
                "NAO_REALIZADO",
                f"DEMO-{checkout_key}",
                pedido_id,
                "DEMO",
            ),
        )
        conexao.commit()
        return {
            "ok": True,
            "demo": True,
            "order": {
                "id": pedido_id,
                "checkout_key": checkout_key,
                "status": "DEMONSTRACAO",
                "total": float(total),
                "payment": metodo,
                "payment_status": "NAO_REALIZADO",
            },
            "payment": {"demo": True, "status": "NAO_REALIZADO"},
        }
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _validar_cpf(documento: str) -> str:
    cpf = re.sub(r"\D", "", documento)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        raise ValueError("Informe um CPF válido para o pagamento.")

    for tamanho in (9, 10):
        soma = sum(int(digito) * peso for digito, peso in zip(cpf[:tamanho], range(tamanho + 1, 1, -1)))
        verificador = (soma * 10 % 11) % 10
        if verificador != int(cpf[tamanho]):
            raise ValueError("Informe um CPF válido para o pagamento.")
    return cpf


def _salvar_checkout(email: str, nome: str, checkout_key: str, carrinho: dict, valor_total: Decimal, metodo: str, resposta_mp: dict) -> tuple[int, dict]:
    status_pagamento, status_pedido = _status_pagamento(resposta_mp.get("status", "pending"))
    dados_interacao = resposta_mp.get("point_of_interaction", {}).get("transaction_data", {})
    detalhes_transacao = resposta_mp.get("transaction_details", {})
    pagamento_id = str(resposta_mp.get("id", ""))
    if not pagamento_id:
        raise ValueError("Mercado Pago não retornou o identificador do pagamento.")

    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        usuario = cursor.fetchone()
        if usuario:
            cliente_id = usuario[0]
        else:
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
                (nome, email, uuid.uuid4().hex),
            )
            cliente_id = cursor.lastrowid

        cursor.execute("SELECT id FROM Pedidos WHERE checkout_key = ?", (checkout_key,))
        existente = cursor.fetchone()
        if existente:
            return existente[0], resposta_mp

        cursor.execute(
            "INSERT INTO Pedidos (login_id, total, status, checkout_key) VALUES (?, ?, ?, ?)",
            (cliente_id, float(valor_total), status_pedido, checkout_key),
        )
        pedido_id = cursor.lastrowid

        for produto_id, item in carrinho["itens"].items():
            cursor.execute(
                "INSERT INTO Carrinho (produtos_id, pedido_id, quantidade) VALUES (?, ?, ?)",
                (produto_id, pedido_id, item["quantidade"]),
            )

        cursor.execute(
            """
            INSERT INTO pagamentos (
                email_usuario, valor, forma_pagamento, status, codigo_transacao,
                pedido_id, status_provedor, boleto_url, boleto_codigo, pix_codigo, pix_qr_base64
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                float(Decimal(str(resposta_mp.get("transaction_amount", valor_total)))),
                metodo,
                status_pagamento,
                pagamento_id,
                pedido_id,
                resposta_mp.get("status", ""),
                detalhes_transacao.get("external_resource_url") or resposta_mp.get("ticket_url"),
                resposta_mp.get("barcode", {}).get("content") or detalhes_transacao.get("digitable_line"),
                dados_interacao.get("qr_code"),
                dados_interacao.get("qr_code_base64"),
            ),
        )
        conexao.commit()
        return pedido_id, resposta_mp
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _criar_pedido_mp(dados: dict, metodo: str, checkout_key: str, email: str, nome: str, valor_total: Decimal) -> dict:
    partes_nome = nome.split()
    pagador = {
        "email": email,
        "first_name": partes_nome[0],
        "last_name": " ".join(partes_nome[1:]) if len(partes_nome) > 1 else partes_nome[0],
        "identification": {
            "type": "CPF",
            "number": _validar_cpf(str(dados.get("cpf") or "")),
        },
    }
    pagamento = {
        "transaction_amount": float(valor_total),
        "description": "Pedido NÓRD",
        "payment_method_id": {"PIX": "pix", "BOLETO": "bolbradesco"}.get(metodo),
        "payer": pagador,
        "external_reference": checkout_key,
    }

    if metodo == "CARTAO":
        token = str(dados.get("cardToken") or "").strip()
        metodo_cartao = str(dados.get("cardPaymentMethodId") or "").strip()
        emissor = str(dados.get("cardIssuerId") or "").strip()
        parcelas = int(dados.get("installments") or 1)
        if not token or not metodo_cartao or not emissor:
            raise ValueError("Não foi possível tokenizar o cartão. Confira os dados e tente novamente.")
        if not 1 <= parcelas <= 12:
            raise ValueError("Escolha entre 1 e 12 parcelas.")
        pagamento.update({
            "token": token,
            "payment_method_id": metodo_cartao,
            "issuer_id": emissor,
            "installments": parcelas,
        })
    elif metodo == "BOLETO":
        cep = re.sub(r"\D", "", str(dados.get("cep") or ""))
        rua = str(dados.get("address") or "").strip()
        numero = str(dados.get("addressNumber") or "").strip()
        cidade = str(dados.get("city") or "").strip()
        estado = str(dados.get("state") or "").strip().upper()
        bairro = str(dados.get("neighborhood") or "").strip()
        if len(cep) != 8 or not rua or not numero or not cidade or len(estado) != 2 or not bairro:
            raise ValueError("Preencha CEP, rua, número, bairro, cidade e estado para emitir o boleto.")
        pagador["address"] = {
            "zip_code": cep,
            "street_name": rua,
            "street_number": numero,
            "neighborhood": bairro,
            "city": cidade,
            "federal_unit": estado,
        }

    notification_url = os.environ.get("MERCADOPAGO_NOTIFICATION_URL", "").strip()
    if notification_url:
        destino = urlsplit(notification_url)
        if destino.scheme != "https" or not destino.netloc:
            raise ValueError("MERCADOPAGO_NOTIFICATION_URL precisa ser uma URL pública HTTPS.")
        pagamento["notification_url"] = notification_url

    return mercado_pago.criar_pagamento(pagamento, checkout_key)


def processar_checkout_web(dados: dict) -> dict:
    if not isinstance(dados, dict):
        raise ValueError("Dados do checkout inválidos.")

    nome = str(dados.get("name") or "").strip()
    email = str(dados.get("email") or "").strip().lower()
    metodo = str(dados.get("payment") or "").strip().upper()
    itens = dados.get("items") or []
    checkout_key = str(dados.get("checkoutKey") or "").strip()

    if not nome or not email:
        raise ValueError("Nome e e-mail são obrigatórios.")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("E-mail inválido.")
    if metodo not in {"PIX", "CARTAO", "BOLETO"}:
        raise ValueError("Forma de pagamento inválida.")
    if len(nome) > 100 or len(email) > 100:
        raise ValueError("Nome ou e-mail excede o limite permitido.")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", checkout_key):
        raise ValueError("Identificador de checkout inválido. Atualize a página e tente novamente.")

    carrinho = montar_carrinho_web(itens)
    frete = calcular_frete_simulado(str(dados.get("cep") or ""))
    subtotal_valor = sum(item["preco"] * item["quantidade"] for item in carrinho["itens"].values())
    cupom = str(dados.get("coupon") or "").strip().upper()
    descontos = {"DESCONTO10": Decimal("0.10"), "DESCONTO20": Decimal("0.20")}
    if cupom and cupom not in descontos:
        raise ValueError("Cupom inválido ou expirado.")
    desconto = subtotal_valor * descontos[cupom] if cupom else Decimal("0.00")
    total = subtotal_valor - desconto + frete
    if metodo == "PIX":
        total *= Decimal("0.95")
    total = total.quantize(Decimal("0.01"))

    access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
    public_key = mercado_pago.obter_chave_publica()
    if not access_token and not public_key:
        return _criar_checkout_demo(email, nome, checkout_key, carrinho, total, metodo)
    if not access_token or not public_key:
        raise mercado_pago.ErroMercadoPago(
            "A configuração do Mercado Pago está incompleta. Defina o Access Token e a Public Key, ou remova os dois para usar a demonstração.",
            503,
        )

    pagamento_existente = None
    conexao = conectar_banco()
    try:
        pagamento_existente = conexao.execute(
            """
            SELECT p.pedido_id, p.codigo_transacao, o.total, p.forma_pagamento
            FROM pagamentos p
            JOIN Pedidos o ON o.id = p.pedido_id
            WHERE o.checkout_key = ?
            """,
            (checkout_key,),
        ).fetchone()
    finally:
        conexao.close()
    if pagamento_existente:
        resposta_mp = mercado_pago.consultar_pagamento(pagamento_existente[1])
        _atualizar_status_pedido(pagamento_existente[1], resposta_mp)
        return _resposta_checkout(
            pagamento_existente[0],
            checkout_key,
            Decimal(str(pagamento_existente[2])),
            pagamento_existente[3],
            resposta_mp,
        )

    resposta_mp = _criar_pedido_mp(dados, metodo, checkout_key, email, nome, total)
    pedido_id, resposta_mp = _salvar_checkout(email, nome, checkout_key, carrinho, total, metodo, resposta_mp)
    return _resposta_checkout(pedido_id, checkout_key, total, metodo, resposta_mp)


def _atualizar_status_pedido(pagamento_id: str, dados_provedor: dict) -> dict:
    status_pagamento, status_pedido = _status_pagamento(dados_provedor.get("status", "pending"))
    conexao = conectar_banco()
    try:
        conexao.execute(
            "UPDATE pagamentos SET status = ?, status_provedor = ? WHERE codigo_transacao = ?",
            (status_pagamento, dados_provedor.get("status", ""), str(pagamento_id)),
        )
        conexao.execute(
            """
            UPDATE Pedidos SET status = ?
            WHERE id = (SELECT pedido_id FROM pagamentos WHERE codigo_transacao = ?)
            """,
            (status_pedido, str(pagamento_id)),
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()
    return dados_provedor


def consultar_status_pedido(checkout_key: str) -> dict:
    conexao = conectar_banco()
    try:
        pedido = conexao.execute(
            """
            SELECT o.id, o.total, o.status, p.codigo_transacao, p.forma_pagamento
            FROM Pedidos o
            JOIN pagamentos p ON p.pedido_id = o.id
            WHERE o.checkout_key = ?
            """,
            (checkout_key,),
        ).fetchone()
    finally:
        conexao.close()
    if not pedido:
        raise ValueError("Pedido não encontrado.")

    resposta_mp = mercado_pago.consultar_pagamento(pedido[3])
    _atualizar_status_pedido(pedido[3], resposta_mp)
    status_pagamento, status_pedido = _status_pagamento(resposta_mp.get("status", "pending"))
    return {
        "ok": True,
        "order": {
            "id": pedido[0],
            "total": float(pedido[1]),
            "status": status_pedido,
            "payment": pedido[4],
            "payment_status": status_pagamento,
            "status_detail": resposta_mp.get("status_detail", ""),
        },
    }


def validar_assinatura_webhook(assinatura: str, request_id: str, data_id: str, segredo: str) -> bool:
    if not assinatura or not request_id or not data_id or not segredo:
        return False

    partes = {}
    for campo in assinatura.split(","):
        chave, separador, valor = campo.strip().partition("=")
        if separador:
            partes[chave] = valor
    timestamp = partes.get("ts")
    assinatura_recebida = partes.get("v1")
    if not timestamp or not assinatura_recebida:
        return False

    id_manifesto = data_id.lower() if not data_id.isdigit() else data_id
    manifesto = f"id:{id_manifesto};request-id:{request_id};ts:{timestamp};"
    assinatura_esperada = hmac.new(
        segredo.encode("utf-8"),
        manifesto.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(assinatura_recebida, assinatura_esperada)


class LojaRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PASTA_FRONTEND, **kwargs)

    def _send_json(self, status_code: int, payload: dict, set_cookie: str | None = None):
        response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(response)

    def _ler_json(self, limite_bytes: int = 100_000) -> dict:
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError as erro:
            raise ValueError("Tamanho de solicitação inválido.") from erro
        if tamanho <= 0 or tamanho > limite_bytes:
            raise ValueError("Tamanho de solicitação inválido.")
        try:
            payload = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as erro:
            raise ValueError("Solicitação inválida.") from erro
        if not isinstance(payload, dict):
            raise ValueError("Solicitação inválida.")
        return payload

    def _token_sessao(self) -> str:
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except CookieError:
            return ""
        cookie = cookies.get("nord_session")
        return cookie.value if cookie else ""

    def _revogar_sessao(self, token: str):
        if not token:
            return
        conexao = conectar_banco()
        try:
            conexao.execute(
                "DELETE FROM sessoes WHERE token_hash = ?",
                (hashlib.sha256(token.encode("utf-8")).hexdigest(),),
            )
            conexao.commit()
        finally:
            conexao.close()

    def _traduzir_caminho_estatico(self):
        partes = urlsplit(self.path)
        caminho = partes.path
        destino = None
        if caminho.startswith("/CSS/"):
            destino = os.path.join(PASTA_FRONTEND_LEGADO, caminho.lstrip("/"))
        elif caminho == "/store.js":
            destino = os.path.join(PASTA_FRONTEND_LEGADO, "store.js")
        elif caminho.endswith(".html") and caminho != "/index.html":
            destino = os.path.join(PASTA_FRONTEND_LEGADO, os.path.basename(caminho))
        if destino and os.path.isfile(destino):
            caminho = "/" + os.path.relpath(destino, RAIZ_PROJETO).replace(os.sep, "/")
            self.path = caminho + (f"?{partes.query}" if partes.query else "")

    def _cookie_sessao(self, token: str | None = None) -> str:
        secure = "; Secure" if os.environ.get("VERCEL") == "1" else ""
        if token:
            return (
                f"nord_session={token}; Path=/; HttpOnly; SameSite=Lax"
                f"; Max-Age={TEMPO_SESSAO_SEGUNDOS}{secure}"
            )
        return f"nord_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"

    def do_GET(self):
        caminho = urlsplit(self.path)
        if caminho.path == "/api":
            self._send_json(404, {"ok": False, "message": "Rota não encontrada."})
            return
        if caminho.path == "/api/health":
            self._send_json(200, {"ok": True, "status": "online"})
            return
        if caminho.path == "/api/auth/me":
            usuario = obter_usuario_da_sessao(self._token_sessao())
            self._send_json(200, {"ok": True, "user": usuario})
            return
        if caminho.path == "/api/produtos":
            produtos = [
                {
                    "id": produto_id,
                    "name": produto["nome"],
                    "short": produto["resumo"],
                    "price": float(produto["preco"]),
                    "stock": produto["estoque"],
                    "category": produto["categoria"],
                    "description": produto["descricao"],
                    "image": produto["imagem"],
                }
                for produto_id, produto in CATALOGO_WEB.items()
            ]
            self._send_json(200, {"ok": True, "products": produtos})
            return
        if caminho.path == "/api/config":
            self._send_json(200, {
                "mercadoPagoPublicKey": mercado_pago.obter_chave_publica(),
                "paymentMode": (
                    "demo"
                    if not os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
                    and not mercado_pago.obter_chave_publica()
                    else "mercado-pago"
                ),
            })
            return
        if caminho.path.startswith("/api/pedidos/"):
            checkout_key = caminho.path.removeprefix("/api/pedidos/")
            try:
                self._send_json(200, consultar_status_pedido(checkout_key))
            except ValueError as erro:
                self._send_json(404, {"ok": False, "message": str(erro)})
            except mercado_pago.ErroMercadoPago as erro:
                self._send_json(erro.status_http, {"ok": False, "message": str(erro)})
            except Exception:
                logging.exception("Erro ao consultar status do pedido.")
                self._send_json(500, {"ok": False, "message": "Não foi possível consultar o pagamento agora."})
            return
        self._traduzir_caminho_estatico()
        return super().do_GET()

    def do_POST(self):
        caminho = urlsplit(self.path)
        if caminho.path == "/api/mercado-pago/webhook":
            self._receber_webhook(caminho.query)
            return

        if caminho.path == "/api/auth/register":
            try:
                payload = self._ler_json()
                usuario, token = criar_conta(
                    payload.get("name", ""), payload.get("email", ""), payload.get("password", "")
                )
                cookie = self._cookie_sessao(token)
                self._send_json(201, {"ok": True, "user": usuario}, set_cookie=cookie)
            except ValueError as erro:
                self._send_json(400, {"ok": False, "message": str(erro)})
            except Exception:
                logging.exception("Erro ao criar a conta.")
                self._send_json(500, {"ok": False, "message": "Não foi possível criar a conta agora."})
            return

        if caminho.path == "/api/auth/login":
            try:
                payload = self._ler_json()
                email = payload.get("email", "")
                senha = payload.get("password", "")
                if not isinstance(email, str) or not isinstance(senha, str) or not senha:
                    raise ValueError("E-mail ou senha incorretos.")
                usuario, token = autenticar_usuario(email, senha)
                cookie = self._cookie_sessao(token)
                self._send_json(200, {"ok": True, "user": usuario}, set_cookie=cookie)
            except ValueError as erro:
                self._send_json(401, {"ok": False, "message": str(erro)})
            except Exception:
                logging.exception("Erro ao entrar na conta.")
                self._send_json(500, {"ok": False, "message": "Não foi possível entrar na conta agora."})
            return

        if caminho.path == "/api/auth/profile":
            try:
                usuario = obter_usuario_da_sessao(self._token_sessao())
                if not usuario:
                    self._send_json(401, {"ok": False, "message": "Entre na sua conta para salvar o perfil."})
                    return
                payload = self._ler_json(limite_bytes=3_000_000)
                usuario_atualizado = atualizar_perfil(usuario["id"], payload)
                self._send_json(200, {"ok": True, "user": usuario_atualizado})
            except ValueError as erro:
                self._send_json(400, {"ok": False, "message": str(erro)})
            except Exception:
                logging.exception("Erro ao atualizar o perfil.")
                self._send_json(500, {"ok": False, "message": "Não foi possível salvar seu perfil agora."})
            return

        if caminho.path == "/api/auth/logout":
            self._revogar_sessao(self._token_sessao())
            self._send_json(200, {"ok": True}, set_cookie=self._cookie_sessao())
            return

        if caminho.path == "/api/checkout":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > 100_000:
                    self._send_json(400, {"ok": False, "message": "Tamanho de solicitação inválido."})
                    return
                body = self.rfile.read(content_length)
                payload = json.loads(body.decode("utf-8"))
                resultado = processar_checkout_web(payload)
                self._send_json(200, resultado)
            except ValueError as erro:
                self._send_json(400, {"ok": False, "message": str(erro)})
            except mercado_pago.ErroMercadoPago as erro:
                self._send_json(erro.status_http, {"ok": False, "message": str(erro)})
            except Exception:
                logging.exception("Erro inesperado ao processar checkout.")
                self._send_json(500, {"ok": False, "message": "Erro interno ao registrar o pedido. Consulte o terminal do servidor."})
            return

        self.send_response(404)
        self.end_headers()

    def _receber_webhook(self, query: str):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 0 or content_length > 100_000:
                self._send_json(400, {"ok": False, "message": "Tamanho de notificação inválido."})
                return
            body = self.rfile.read(content_length) if content_length else b"{}"
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"ok": False, "message": "Notificação inválida."})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "message": "Notificação inválida."})
            return

        parametros = parse_qs(query)
        data_id = (parametros.get("data.id") or [""])[0]
        tipo = (parametros.get("type") or [payload.get("type", "")])[0]
        if tipo and tipo != "payment":
            self._send_json(200, {"ok": True, "ignored": True})
            return
        if not re.fullmatch(r"\d+", data_id):
            self._send_json(400, {"ok": False, "message": "Identificador do pagamento inválido."})
            return

        segredo = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
        if not segredo:
            self._send_json(503, {"ok": False, "message": "MERCADOPAGO_WEBHOOK_SECRET não está configurado."})
            return
        if not validar_assinatura_webhook(
            self.headers.get("x-signature", ""),
            self.headers.get("x-request-id", ""),
            data_id,
            segredo,
        ):
            self._send_json(401, {"ok": False, "message": "Assinatura da notificação inválida."})
            return

        conexao = conectar_banco()
        try:
            pagamento = conexao.execute(
                "SELECT 1 FROM pagamentos WHERE codigo_transacao = ?",
                (data_id,),
            ).fetchone()
        finally:
            conexao.close()
        if not pagamento:
            self._send_json(200, {"ok": True, "ignored": True})
            return

        try:
            dados_pagamento = mercado_pago.consultar_pagamento(data_id)
            if str(dados_pagamento.get("id", "")) != data_id:
                raise ValueError("O ID consultado não corresponde ao pagamento notificado.")
            _atualizar_status_pedido(data_id, dados_pagamento)
            self._send_json(200, {"ok": True})
        except mercado_pago.ErroMercadoPago as erro:
            logging.warning("Não foi possível consultar o pagamento notificado: %s", erro)
            self._send_json(502, {"ok": False, "message": "Não foi possível confirmar a notificação com o provedor."})
        except Exception:
            logging.exception("Erro ao atualizar pagamento recebido por webhook.")
            self._send_json(500, {"ok": False, "message": "Erro interno ao processar a notificação."})


def iniciar_servidor(host: str = "127.0.0.1", porta: int = 8000):
    inicializar_todas_as_tabelas()
    servidor = ThreadingHTTPServer((host, porta), LojaRequestHandler)
    print(f"Servidor da loja rodando em http://{host}:{porta}")
    print("Acesse a página inicial em: http://localhost:8000/index.html")
    servidor.serve_forever()


def executar_cli():
    print("O checkout pelo terminal está desativado para impedir pagamentos simulados.")
    print("Inicie o servidor e conclua a compra pelo checkout web.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"--cli", "cli"}:
        executar_cli()
    else:
        iniciar_servidor()
