import os
import re
import sqlite3
import uuid
from decimal import Decimal

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETO = os.path.dirname(DIRETORIO_ATUAL)
PASTA_DATABASE = os.path.join(RAIZ_PROJETO, "database")
CAMINHO_BANCO = os.path.join(PASTA_DATABASE, "loja.db")

os.makedirs(PASTA_DATABASE, exist_ok=True)


def inicializar_todas_as_tabelas():
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(255) NOT NULL,
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
            data_transacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.commit()
    conexao.close()


def usuario_existe(email: str) -> bool:
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
    resultado = cursor.fetchone()
    conexao.close()
    return resultado is not None


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

    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome_completo, email, senha)
    )
    usuario_id = cursor.lastrowid
    conexao.commit()
    conexao.close()

    return {"id": usuario_id, "nome": nome_completo, "email": email}


def criar_carrinho() -> dict:
    return {'itens': {}, 'cupom': None}


def adicionar_item(carrinho: dict, produto_id: int, nome: str, preco: Decimal, quantidade: int, estoque: dict) -> dict:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    qtd_atual = carrinho['itens'].get(produto_id, {}).get('quantidade', 0)
    qtd_total = qtd_atual + quantidade

    if produto_id not in estoque or qtd_total > estoque[produto_id]['estoque']:
        raise ValueError(f"Estoque insuficiente! Disponível: {estoque[produto_id]['estoque']} un.")

    carrinho['itens'][produto_id] = {
        'nome': nome,
        'preco': preco,
        'quantidade': qtd_total
    }
    return carrinho


def calcular_frete_simulado(cep: str) -> Decimal:
    cep_limpo = cep.strip().replace('-', '')
    if not re.match(r"^\d{8}$", cep_limpo):
        raise ValueError("CEP inválido! Digite exatamente 8 números.")
    return Decimal("15.00") if cep_limpo.startswith(('0', '1')) else Decimal("25.00")


def aplicar_cupom(carrinho: dict, cupom_nome: str) -> dict:
    cupom_limpo = cupom_nome.strip().upper()
    cupons_validos = {
        "DESCONTO10": Decimal("0.10"),
        "DESCONTO20": Decimal("0.20")
    }

    if cupom_limpo not in cupons_validos:
        raise ValueError("Cupom inválido ou expirado.")

    carrinho['cupom'] = {'nome': cupom_limpo, 'desconto': cupons_validos[cupom_limpo]}
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
    for produto_id, item in carrinho['itens'].items():
        estoque[produto_id]['estoque'] -= item['quantidade']

    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO Pedidos (login_id, total, status) VALUES (?, ?, ?)
    """, (cliente_id, float(resumo['total']), "AGUARDANDO_PAGAMENTO"))
    pedido_id = cursor.lastrowid

    for produto_id, item in carrinho['itens'].items():
        cursor.execute("""
            INSERT INTO Carrinho (produtos_id, pedido_id, quantidade) VALUES (?, ?, ?)
        """, (produto_id, pedido_id, item['quantidade']))

    conexao.commit()
    conexao.close()

    return {
        "pedido_id": pedido_id,
        "cliente_id": cliente_id,
        "total": resumo['total'],
        "status": "AGUARDANDO_PAGAMENTO"
    }


def processar_pagamento(email: str, forma: str, valor: float, **dados) -> dict:
    forma = forma.upper()

    if forma == "PIX":
        valor_final = round(valor * 0.95, 2)
        codigo = f"00020126580014br.gov.bcb.pix-{uuid.uuid4()}"
        status = "Aprovado"

    elif forma == "CARTAO":
        num_cartao = dados.get("cartao", "").strip()
        cvv = dados.get("cvv", "").strip()
        parcelas = dados.get("parcelas", 1)

        if not re.match(r"^\d{16}$", num_cartao):
            raise ValueError("O cartão deve ter 16 dígitos.")
        if not re.match(r"^\d{3,4}$", cvv):
            raise ValueError("CVV deve ter 3 ou 4 dígitos.")
        if not (1 <= parcelas <= 12):
            raise ValueError("Parcelamento permitido de 1x até 12x.")
        if (valor / parcelas) < 10.0:
            raise ValueError("A parcela mínima é de R$ 10,00.")

        valor_final = round(valor, 2)
        codigo = f"AUTH-{str(uuid.uuid4())[:8].upper()}"
        status = "Aprovado"

    elif forma == "BOLETO":
        valor_final = round(valor, 2)
        codigo = f"34191.79001 {uuid.uuid4().int % 100000:.0f}.671234 5.890000000{int(valor)}"
        status = "Pendente"

    else:
        raise ValueError("Opção de pagamento inválida.")

    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
    cursor.execute("""
        INSERT INTO pagamentos (email_usuario, valor, forma_pagamento, status, codigo_transacao)
        VALUES (?, ?, ?, ?, ?)
    """, (email, valor_final, forma, status, codigo))
    conexao.commit()
    conexao.close()

    return {
        "sucesso": True,
        "forma_pagamento": forma,
        "valor_final": valor_final,
        "status": status,
        "codigo_transacao": codigo
    }


if __name__ == "__main__":
    inicializar_todas_as_tabelas()

    # Produtos cadastrados na loja
    CATALOGO_PRODUTOS = {
        1: {"nome": "Teclado Gamer Mechanical", "preco": Decimal("150.00"), "estoque": 10},
        2: {"nome": "Mouse Pad Extra Grande", "preco": Decimal("40.00"), "estoque": 5},
        3: {"nome": "Headset Surround 7.1", "preco": Decimal("220.00"), "estoque": 8},
        4: {"nome": "Monitor 144Hz Full HD", "preco": Decimal("950.00"), "estoque": 3}
    }

    print("==================================================")
    print("           BEM-VINDO À LOJA VIRTUAL              ")
    print("==================================================")

    # 1. PASSO: CADASTRO DO USUÁRIO
    print("\n--- PASSO 1: CADASTRO DE USUÁRIO ---")
    usuario_logado = None

    while not usuario_logado:
        try:
            nome = input("Digite seu Primeiro Nome: ")
            sobrenome = input("Digite seu Sobrenome: ")
            email = input("Digite seu E-mail: ")
            senha = input("Digite sua Senha (letras e números): ")

            usuario_logado = cadastrar_usuario(nome, sobrenome, email, senha)
            print(f"\nCadastro realizado com sucesso! Bem-vindo(a), {usuario_logado['nome']}!")
        except ValueError as err:
            print(f" Erro no cadastro: {err}\nTente novamente.\n")

    # 2. PASSO: SELEÇÃO DE PRODUTOS
    carrinho = criar_carrinho()
    
    while True:
        print("\n--- PASSO 2: CATÁLOGO DE PRODUTOS ---")
        for id_prod, prod in CATALOGO_PRODUTOS.items():
            print(f"[{id_prod}] {prod['nome']} - R$ {prod['preco']:.2f} (Estoque: {prod['estoque']})")

        try:
            opcao = input("\nDigite o ID do produto que deseja (ou 'F' para finalizar seleção): ").strip().upper()
            if opcao == 'F':
                if not carrinho['itens']:
                    print("Seu carrinho está vazio! Adicione pelo menos 1 produto.")
                    continue
                break

            prod_id = int(opcao)
            if prod_id not in CATALOGO_PRODUTOS:
                print("Produto não encontrado!")
                continue

            qtd = int(input(f"Quantidade de '{CATALOGO_PRODUTOS[prod_id]['nome']}': "))
            adicionar_item(carrinho, prod_id, CATALOGO_PRODUTOS[prod_id]['nome'], CATALOGO_PRODUTOS[prod_id]['preco'], qtd, CATALOGO_PRODUTOS)
            print(f"Item adicionado ao carrinho!")

        except ValueError as err:
            print(f"Entrada inválida: {err}")

    # 3. PASSO: FRETE E CUPOM
    print("\n--- PASSO 3: FRETE E CUPOM ---")
    frete_calculado = None
    while not frete_calculado:
        try:
            cep = input("Digite o CEP para entrega (8 números): ")
            frete_calculado = calcular_frete_simulado(cep)
        except ValueError as err:
            print(f"{err}")

    usar_cupom = input("Possui cupom de desconto? (S/N): ").strip().upper()
    if usar_cupom == 'S':
        try:
            cod_cupom = input("Digite o código do cupom (Ex: DESCONTO10): ")
            aplicar_cupom(carrinho, cod_cupom)
            print("Cupom aplicado com sucesso!")
        except ValueError as err:
            print(f"{err} Continuando sem cupom.")

    resumo = calcular_total_carrinho(carrinho, frete_calculado)

    print("\n==================================================")
    print("               RESUMO DO CARRINHO                 ")
    print("==================================================")
    for item in carrinho['itens'].values():
        print(f"- {item['nome']} (x{item['quantidade']}): R$ {item['preco'] * item['quantidade']:.2f}")
    print(f"\nSubtotal: R$ {resumo['subtotal']:.2f}")
    print(f"Desconto: R$ {resumo['desconto']:.2f}")
    print(f"Frete:    R$ {resumo['frete']:.2f}")
    print(f"TOTAL:    R$ {resumo['total']:.2f}")

    # 4. PASSO: CRIAÇÃO DO PEDIDO
    pedido = fechar_pedido(usuario_logado['id'], carrinho, resumo, CATALOGO_PRODUTOS)
    print(f"\nPedido #{pedido['pedido_id']} gerado com sucesso!")

    # 5. PASSO: PROCESSAMENTO DO PAGAMENTO
    print("\n--- PASSO 4: PAGAMENTO ---")
    print("Formas disponíveis: [1] PIX (5% de desconto) | [2] CARTAO | [3] BOLETO")

    pagamento_concluido = False
    while not pagamento_concluido:
        opcao_pag = input("Escolha a opção (1, 2 ou 3): ").strip()

        try:
            if opcao_pag == '1':
                res = processar_pagamento(usuario_logado['email'], "PIX", float(resumo['total']))
                print(f"\nPagamento via PIX Aprovado!")
                print(f"Valor com desconto: R$ {res['valor_final']:.2f}")
                print(f"Código PIX: {res['codigo_transacao']}")

            elif opcao_pag == '2':
                cartao = input("Digite o número do cartão (16 dígitos): ")
                cvv = input("Digite o CVV (3 ou 4 dígitos): ")
                parcelas = int(input("Digite a quantidade de parcelas (1 a 12): "))

                res = processar_pagamento(usuario_logado['email'], "CARTAO", float(resumo['total']), cartao=cartao, cvv=cvv, parcelas=parcelas)
                print(f"\nPagamento no Cartão Aprovado!")
                print(f"Autorização: {res['codigo_transacao']}")

            elif opcao_pag == '3':
                res = processar_pagamento(usuario_logado['email'], "BOLETO", float(resumo['total']))
                print(f"\nBoleto Gerado com Sucesso!")
                print(f"Linha Digitável: {res['codigo_transacao']}")

            else:
                print(" Opção inválida!")
                continue

            pagamento_concluido = True

        except ValueError as err:
            print(f" Erro no pagamento: {err}\nTente novamente.\n")

    print("\n==================================================")
    print("    COMPRA FINALIZADA E REGISTRADA NO BANCO!     ")
    print("==================================================")