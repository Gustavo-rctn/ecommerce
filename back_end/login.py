import os
import re
import sqlite3

# =========================================================================================================

# Pega o caminho da pasta raiz do projeto (subindo um nível a partir de 'back_end')
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETO = os.path.dirname(DIRETORIO_ATUAL)
PASTA_DATABASE = os.path.join(RAIZ_PROJETO, "database")
CAMINHO_BANCO = os.path.join(PASTA_DATABASE, "loja.db")

# Garante que a pasta 'database' existe antes de conectar
os.makedirs(PASTA_DATABASE, exist_ok=True)


# =========================================================================================================

def inicializar_banco():
    """Cria a tabela de usuários caso ela ainda não exista."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()


def usuario_existe(email: str) -> bool:
    """Consulta o banco de dados para verificar se o e-mail já está cadastrado."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
    resultado = cursor.fetchone()

    conexao.close()
    return resultado is not None


def salvar_usuario_no_banco(nome_completo: str, email: str, senha: str):
    """Insere o novo usuário validado no banco de dados."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome_completo, email, senha)
    )

    conexao.commit()
    conexao.close()


# =========================================================================================================

def cadastrar_usuario(nome: str, sobrenome: str, email: str, senha: str) -> dict:
    # 1. Garantir que a tabela existe no SQLite
    inicializar_banco()

    # 2. Tratamento de espaços e caixa baixa
    nome = nome.strip()
    sobrenome = sobrenome.strip()
    email = email.strip().lower()

    # 3. Presença dos campos
    if not nome or not sobrenome or not email or not senha:
        raise ValueError("Todos os campos são obrigatórios.")

    # 4. Validações do NOME
    if len(nome) < 3 or len(nome) > 50:
        raise ValueError("O nome deve ter entre 3 e 50 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", nome):
        raise ValueError("O nome deve conter apenas letras e espaços.")

    # 5. Validações do SOBRENOME
    if len(sobrenome) < 3 or len(sobrenome) > 50:
        raise ValueError("O sobrenome deve ter entre 3 e 50 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", sobrenome):
        raise ValueError("O sobrenome deve conter apenas letras e espaços.")

    # 6. Validações do EMAIL
    if len(email) > 100:
        raise ValueError("O email deve ter no máximo 100 caracteres.")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("O email fornecido não é válido.")

    # 7. Validações da SENHA
    if len(senha) < 6 or len(senha) > 20:
        raise ValueError("A senha deve ter entre 6 e 20 caracteres.")
    if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)", senha):
        raise ValueError("A senha deve conter pelo menos uma letra e um número.")

    # 8. Checagem no banco de dados
    if usuario_existe(email):
        raise ValueError("O email fornecido já está em uso.")

    # 9. Gravando no SQLite
    nome_completo = f"{nome} {sobrenome}"
    salvar_usuario_no_banco(nome_completo, email, senha)

    return {"nome": nome_completo, "email": email}


# =========================================================================================================

if __name__ == "__main__":
    nome_usuario = input('Digite seu nome: ').strip().title()
    sobrenome_usuario = input('Digite seu sobrenome: ').strip().title()
    email_usuario = input('Digite seu email: ')
    senha_usuario = input('Digite sua senha: ')

    try:
        update = cadastrar_usuario(nome_usuario, sobrenome_usuario, email_usuario, senha_usuario)
        print("\n[+] Usuário cadastrado com sucesso:", update)
    except ValueError as erro:
        print(f"\n[-] Erro no cadastro: {erro}")


def listar_todos_usuarios():
    """Busca e exibe todos os usuários salvos na tabela."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    cursor.execute("SELECT id, nome, email FROM usuarios")
    usuarios = cursor.fetchall()
    conexao.close()

    print("\n--- USUÁRIOS NO BANCO DE DADOS ---")
    for u in usuarios:
        print(f"ID: {u[0]} | Nome: {u[1]} | E-mail: {u[2]}")