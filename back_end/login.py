import re
import sqlite3

def usuario_existe(email: str) -> bool:
    """Consulta o banco de dados para verificar se o e-mail já está cadastrado."""
    # 1. Abre a conexão com o arquivo de banco
    conexao = sqlite3.connect("database/loja.db")
    cursor = conexao.cursor()

    # 2. Executa a busca (o '?' evita ataques de SQL Injection)
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
    
    # 3. Pega o primeiro resultado encontrado
    resultado = cursor.fetchone()

    # 4. Fecha a conexão
    conexao.close()

    # Se resultado for diferente de None, o usuário EXISTE (retorna True)
    return resultado is not None
#==========================================================================================================
def salvar_usuario_no_banco(nome: str, email: str, senha: str):
    """Insere o novo usuário validado no banco de dados."""
    conexao = sqlite3.connect("database/loja.db")
    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome, email, senha)
    )

    conexao.commit() # Confirma a gravação dos dados
    conexao.close()

#==================================================================================================================

def cadastrar_usuario(nome, sobrenome, email, senha):
    # 1. Tratamento de espaços nas pontas
    nome = nome.strip()
    sobrenome = sobrenome.strip()
    email = email.strip().lower()

    # 2. Presença dos campos
    if not nome or not email or not senha:
        raise ValueError("Todos os campos são obrigatórios.")

    # 3. Validações do NOME (Tamanho e Caracteres)
    if len(nome) < 3 or len(nome) > 50:
        raise ValueError("O nome deve ter entre 3 e 50 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", nome):
        raise ValueError("O nome deve conter apenas letras e espaços.")
    #4. Validações do SOBRENOME (Tamanho e Caracteres)
    if len(sobrenome) < 3 or len(sobrenome) > 50:
        raise ValueError("O nome deve ter entre 3 e 50 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", sobrenome):
        raise ValueError("O nome deve conter apenas letras e espaços.")

    # 5. Validações do EMAIL (Tamanho e Formato)
    if len(email) > 100:
        raise ValueError("O email deve ter no máximo 100 caracteres.")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("O email fornecido não é válido.")

    # 6. Validações da SENHA (Tamanho e Regra de Segurança)
    if len(senha) < 6 or len(senha) > 20:
        raise ValueError("A senha deve ter entre 6 e 20 caracteres.")
    if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)", senha):
        raise ValueError("A senha deve conter pelo menos uma letra e um número.")



    # 6. Checagem no banco de dados (SÓ APÓS PASSAR EM TODAS AS REGRAS)
    if usuario_existe(email):
        raise ValueError("O email fornecido já está em uso.")
        # 7. Estrutura pronta para salvar no seu dicionário/JSON/BD
    novo_usuario = {
        "nome": nome,
        "email": email,
        "senha": senha  # No futuro aplicaremos HASH aqui pra segurança!
    }

    salvar_usuario_no_banco(nome, email, senha)
    return {"nome": nome, "email": email}


nome_usuario = input('Digite seu nome: ').strip().title()
sobrenome_usuario = input('Digite seu sobrenome: ').strip().title()
email_usuario = input('Digite seu email: ')
senha_usuario = input('Digite sua senha: ')


#=========================================================================================================



try:
    update = cadastrar_usuario(nome_usuario, sobrenome_usuario, email_usuario, senha_usuario)
    print("Usuário cadastrado com sucesso:", update)
except ValueError as erro:
    print(f"Erro no cadastro: {erro}")






