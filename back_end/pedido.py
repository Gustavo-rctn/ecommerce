import os
import sqlite3

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(PASTA_ATUAL)
PASTA_DB = os.path.join(RAIZ, "database")
BANCO_BD = os.path.join(PASTA_DB, "loja.db")

os.makedirs(PASTA_DB, exist_ok=True)


def preparar_banco():
    conexao = sqlite3.connect(BANCO_BD)
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(255) NOT NULL,
            FOREIGN KEY (login_id) REFERENCES Login (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Carrinho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produtos_id INTEGER NOT NULL,
            pedido_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (produtos_id) REFERENCES produto (id),
            FOREIGN KEY (pedido_id) REFERENCES Pedidos (id)
        )
    """)
    conexao.commit()
    conexao.close()


def guardar_pedido(cliente_id: int, total: float, status: str, itens_carrinho: dict) -> int:
    conexao = sqlite3.connect(BANCO_BD)
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO Pedidos (login_id, total, status)
        VALUES (?, ?, ?)
    """, (cliente_id, total, status))
    
    novo_pedido_id = cursor.lastrowid

    for produto_id, dados in itens_carrinho.items():
        cursor.execute("""
            INSERT INTO Carrinho (produtos_id, pedido_id, quantidade)
            VALUES (?, ?, ?)
        """, (produto_id, novo_pedido_id, dados["quantidade"]))

    conexao.commit()
    conexao.close()
    
    return novo_pedido_id


def criar_pedido(cliente_id: int, carrinho: dict) -> dict:
    preparar_banco()

    if not carrinho.get('itens'):
        raise ValueError("Carrinho vazio! Adicione algo antes de fechar a compra.")

    itens_carrinho = carrinho['itens']

   
    total = sum(dados['preco'] * dados['quantidade'] for dados in itens_carrinho.values())

    status_inicial = "Aguardando Pagamento"

    pedido_id = guardar_pedido(
        cliente_id=cliente_id,
        total=round(total, 2),
        status=status_inicial,
        itens_carrinho=itens_carrinho
    )

    return {
        "sucesso": True,
        "pedido_id": pedido_id,
        "cliente_id": cliente_id,
        "total": round(total, 2),
        "status": status_inicial
    }