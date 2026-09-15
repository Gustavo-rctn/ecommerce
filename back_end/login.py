import re

def cadastrar_usuario(nome, email, senha):
    # 1. Tratamento de espaços nas pontas
    nome = nome.strip()
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
    if len(nome) < 3 or len(nome) > 50:
        raise ValueError("O nome deve ter entre 3 e 50 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", nome):
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

    return novo_usuario


nome_usuario = input('Digite seu nome: ').strip.title()
sobrenome_usuario = input('Digite seu sobrenome: ').strip.title()
email_usuario = input('Digite seu email: ')
senha_usuario = input('Digite sua senha: ')

update = cadastrar_usuario(nome_usuario, sobrenome_usuario, email_usuario, senha_usuario)


