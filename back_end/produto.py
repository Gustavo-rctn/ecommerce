from decimal import Decimal


def criar_pedido(carrinho: dict, resumo_financeiro: dict, cliente_id: int, estoque: dict) -> dict:
    if not carrinho['itens']:
        raise ValueError("Não é possível criar um pedido com o carrinho vazio.")

    for produto_id, item in carrinho['itens'].items():
        quantidade = item['quantidade']
        if produto_id not in estoque or estoque[produto_id] < quantidade:
            raise ValueError(f"Estoque insuficiente para o produto {produto_id}.")

    for produto_id, item in carrinho['itens'].items():
        estoque[produto_id] -= item['quantidade']

    return {
        'pedido_id': 1,
        'cliente_id': cliente_id,
        'itens': carrinho['itens'].copy(),
        'financeiro': resumo_financeiro,
        'status': 'AGUARDANDO_PAGAMENTO'
    }


if __name__ == "__main__":
    carrinho_exemplo = {
        'itens': {
            1: {'nome': 'Teclado Gamer', 'preco': Decimal('150.00'), 'quantidade': 2},
            2: {'nome': 'Mouse Pad', 'preco': Decimal('40.00'), 'quantidade': 1}
        },
        'cupom': {'nome': 'DESCONTO10', 'desconto': Decimal('0.10')}
    }

    resumo_exemplo = {
        'subtotal': Decimal('340.00'),
        'desconto': Decimal('34.00'),
        'frete': Decimal('15.00'),
        'total': Decimal('321.00')
    }

    estoque_loja = {
        1: 10,
        2: 5
    }

    pedido = criar_pedido(carrinho_exemplo, resumo_exemplo, 101, estoque_loja)

    print("--- PEDIDO CRIADO ---")
    print(f"ID Pedido: {pedido['pedido_id']}")
    print(f"Status: {pedido['status']}")
    print(f"Estoque Atualizado do Produto 1: {estoque_loja[1]}")
    print(f"Estoque Atualizado do Produto 2: {estoque_loja[2]}")