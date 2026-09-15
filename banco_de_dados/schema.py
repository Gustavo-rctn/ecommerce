# database/schema.py
import sqlite3

def criar_banco():
    # Conecta ou cria o arquivo de banco de dados na pasta
    conexao = sqlite3.connect("database/loja.db")
    cursor = conexao.cursor()

    # Cria a tabela de usuários se ela ainda não existir
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
    print("Banco de dados e tabela inicializados com sucesso!")

if __name__ == "__main__":
    criar_banco()