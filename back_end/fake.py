import argparse
from decimal import Decimal

from faker import Faker


PRODUTOS_MODELO = (
    {
        "nome": "Webcam Full HD",
        "resumo": "Imagem nítida para chamadas",
        "categoria": "IMAGEM",
        "descricao": "Imagem em alta definição para reuniões, aulas e transmissões.",
        "preco_minimo": 149,
        "preco_maximo": 399,
        "imagem": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Microfone USB",
        "resumo": "Voz clara nas gravações",
        "categoria": "ÁUDIO",
        "descricao": "Captação de voz clara para chamadas, gravações e transmissões.",
        "preco_minimo": 129,
        "preco_maximo": 499,
        "imagem": "https://images.unsplash.com/photo-1599669454699-248893623440?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Mouse Gamer RGB",
        "resumo": "Precisão para cada movimento",
        "categoria": "SETUP",
        "descricao": "Um mouse confortável e preciso para o trabalho ou para jogar.",
        "preco_minimo": 79,
        "preco_maximo": 299,
        "imagem": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Base Refrigerada para Notebook",
        "resumo": "Mais ventilação para o notebook",
        "categoria": "SETUP",
        "descricao": "Ajuda a manter o notebook ventilado durante o uso diário.",
        "preco_minimo": 89,
        "preco_maximo": 249,
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "SSD Externo",
        "resumo": "Armazenamento portátil",
        "categoria": "ACESSÓRIOS",
        "descricao": "Leve seus arquivos e projetos com você com praticidade.",
        "preco_minimo": 199,
        "preco_maximo": 899,
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Caixa de Som Bluetooth",
        "resumo": "Música em qualquer ambiente",
        "categoria": "ÁUDIO",
        "descricao": "Som portátil para acompanhar sua rotina em casa ou no trabalho.",
        "preco_minimo": 99,
        "preco_maximo": 449,
        "imagem": "https://images.unsplash.com/photo-1599669454699-248893623440?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Cadeira Ergonômica",
        "resumo": "Conforto para longas sessões",
        "categoria": "SETUP",
        "descricao": "Uma opção confortável para o escritório ou espaço de jogos.",
        "preco_minimo": 599,
        "preco_maximo": 1799,
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Hub USB-C",
        "resumo": "Mais conexões para seus dispositivos",
        "categoria": "ACESSÓRIOS",
        "descricao": "Expanda as conexões do seu computador com um acessório compacto.",
        "preco_minimo": 69,
        "preco_maximo": 299,
        "imagem": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Suporte para Notebook",
        "resumo": "Organize melhor sua mesa",
        "categoria": "SETUP",
        "descricao": "Eleve o notebook e aproveite melhor o espaço de trabalho.",
        "preco_minimo": 59,
        "preco_maximo": 199,
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Teclado Sem Fio",
        "resumo": "Liberdade para organizar o setup",
        "categoria": "SETUP",
        "descricao": "Um teclado prático para manter a mesa organizada.",
        "preco_minimo": 99,
        "preco_maximo": 399,
        "imagem": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Luminária LED para Monitor",
        "resumo": "Iluminação funcional para a mesa",
        "categoria": "ACESSÓRIOS",
        "descricao": "Ilumine sua área de trabalho sem ocupar espaço na mesa.",
        "preco_minimo": 89,
        "preco_maximo": 299,
        "imagem": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
    },
    {
        "nome": "Controle Sem Fio",
        "resumo": "Conforto para jogar",
        "categoria": "SETUP",
        "descricao": "Mais liberdade e conforto para jogar no computador.",
        "preco_minimo": 149,
        "preco_maximo": 499,
        "imagem": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=80",
    },
)


def gerar_produtos_falsos(quantidade: int = 8, seed: int = 42, primeiro_id: int = 5) -> dict:
    """Gera produtos de demonstração com o mesmo formato do catálogo da loja."""
    if quantidade <= 0 or quantidade > len(PRODUTOS_MODELO):
        raise ValueError(f"A quantidade deve estar entre 1 e {len(PRODUTOS_MODELO)}.")
    if primeiro_id <= 0:
        raise ValueError("O primeiro ID deve ser maior que zero.")

    fake = Faker("pt_BR")
    fake.seed_instance(seed)
    modelos = fake.random_elements(
        elements=PRODUTOS_MODELO,
        length=quantidade,
        unique=True,
    )

    return {
        primeiro_id + indice: {
            "nome": modelo["nome"],
            "resumo": modelo["resumo"],
            "preco": Decimal(f"{fake.random_int(modelo['preco_minimo'], modelo['preco_maximo'])}.90"),
            "estoque": fake.random_int(3, 30),
            "categoria": modelo["categoria"],
            "descricao": modelo["descricao"],
            "imagem": modelo["imagem"],
        }
        for indice, modelo in enumerate(modelos)
    }


def quantidade_positiva(valor: str) -> int:
    try:
        quantidade = int(valor)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("Informe um número inteiro.") from erro
    if quantidade <= 0 or quantidade > len(PRODUTOS_MODELO):
        raise argparse.ArgumentTypeError(
            f"A quantidade deve estar entre 1 e {len(PRODUTOS_MODELO)}."
        )
    return quantidade


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera produtos fictícios para o catálogo da loja.")
    parser.add_argument("--quantidade", type=quantidade_positiva, default=8)
    parser.add_argument("--seed", type=int, default=42, help="Seed para gerar os mesmos dados novamente.")
    argumentos = parser.parse_args()
    produtos = gerar_produtos_falsos(argumentos.quantidade, argumentos.seed)

    print(f"{len(produtos)} produtos fictícios gerados:")
    for produto in produtos.values():
        print(f"- {produto['nome']} | R$ {produto['preco']:.2f} | estoque: {produto['estoque']}")


if __name__ == "__main__":
    main()
