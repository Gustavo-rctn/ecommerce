import sqlite3

def limpar_banco(caminho_db: str = "database/loja.db"):
    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tabelas = cursor.fetchall()

    for tabela in tabelas:
        nome_tabela = tabela[0]
        cursor.execute(f"DELETE FROM {nome_tabela};")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name=?;", (nome_tabela,))

    cursor.execute("PRAGMA foreign_keys = ON;")

    conexao.commit()
    conexao.close()

if __name__ == "__main__":
    limpar_banco()