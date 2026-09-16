import re
from decimal import Decimal


def criar_carrinho() -> dict:
    return {
        'itens': {},
        'cupom': None
    }


def adicionar_item(carrinho: dict, produto_id: int, nome: str, preco: Decimal, quantidade: int, estoque_disponivel: int) -> dict:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")
    if preco <= Decimal("0.00"):
        raise ValueError("O preço deve ser maior que zero.")


    if produto_id in carrinho['itens']:
        qtd_que_ja_tinha = carrinho['itens'][produto_id]['quantidade']
    else:
        qtd_que_ja_tinha = 0

    qtd_total = qtd_que_ja_tinha + quantidade

    if qtd_total > estoque_disponivel:
        raise ValueError("Estoque insuficiente.")

    carrinho['itens'][produto_id] = {
        'nome': nome,
        'preco': preco,
        'quantidade': qtd_total
    }

    return carrinho


def remover_item(carrinho: dict, produto_id: int) -> dict:
    if produto_id not in carrinho['itens']:
        raise ValueError("Produto não encontrado no carrinho.")
    
    del carrinho['itens'][produto_id]
    return carrinho


def calcular_frete_simulado(cep: str) -> Decimal:
    cep = cep.strip().replace('-', '')

    if not re.match(r"^\d{8}$", cep):
        raise ValueError('CEP inválido. Digite 8 números')

    if cep.startswith(('0', '1')):
        frete = "15.00"
    else:
        frete = "25.00"

    return Decimal(frete)


def aplicar_cupom(carrinho: dict, cupom_nome: str, cupom_desconto: Decimal) -> dict:
    cupom_nome = cupom_nome.strip().upper()

    if not cupom_nome:
        raise ValueError('Cupom inválido.')

    if cupom_desconto <= Decimal('0.00') or cupom_desconto > Decimal('1.00'):
        raise ValueError('Porcentagem de desconto inválida.')

    carrinho['cupom'] = {
        'nome': cupom_nome,
        'desconto': cupom_desconto
    }

    return carrinho


def calcular_total_carrinho(carrinho: dict, frete: Decimal) -> dict:
    subtotal = Decimal("0.00")

    for item in carrinho["itens"].values():
        subtotal += item["preco"] * item["quantidade"]

    if carrinho["cupom"] is not None:
        desconto = subtotal * carrinho["cupom"]["desconto"]
    else:
        desconto = Decimal("0.00")

    total = subtotal - desconto + frete

    return {
        "subtotal": subtotal,
        "desconto": desconto,
        "frete": frete,
        "total": total
    }


# ===========================================================================================================

if __name__ == "__main__":
    meu_carrinho = criar_carrinho()

    adicionar_item(meu_carrinho, 1, "Teclado Gamer", Decimal("150.00"), 2, 10)
    adicionar_item(meu_carrinho, 2, "Mouse Pad", Decimal("40.00"), 1, 5)

    frete = calcular_frete_simulado("01310000")

    aplicar_cupom(meu_carrinho, "DESCONTO10", Decimal("0.10"))

    resumo = calcular_total_carrinho(meu_carrinho, frete)

    print("\n--- RESUMO DO CARRINHO ---")
    print(f"Subtotal: R$ {resumo['subtotal']}")
    print(f"Desconto: R$ {resumo['desconto']:.2f}")
    print(f"Frete:    R$ {resumo['frete']}")
    print(f"Total:    R$ {resumo['total']:.2f}\n")