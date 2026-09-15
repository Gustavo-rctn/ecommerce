import os
import sqlite3
import re
import uuid
from decimal import Decimal


DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETO = os.path.dirname(DIRETORIO_ATUAL)
PASTA_DATABASE = os.path.join(RAIZ_PROJETO, "database")
CAMINHO_BANCO = os.path.join(PASTA_DATABASE, "loja.db")

os.makedirs(PASTA_DATABASE, exist_ok=True)



# PERSISTÊNCIA E OPERAÇÕES DO BANCO DE DADOS
# =========================================================================================================

def inicializar_banco_pagamentos():
    """Cria a tabela de pagamentos no SQLite se não existir."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
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


def salvar_pagamento_no_banco(email: str, valor: float, forma_pagamento: str, status: str, codigo_transacao: str):
    """Insere a transação financeira no banco de dados."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    cursor = conexao.cursor()
    
    valor_formatado = float(round(Decimal(str(valor)), 2))

    cursor.execute("""
        INSERT INTO pagamentos (email_usuario, valor, forma_pagamento, status, codigo_transacao)
        VALUES (?, ?, ?, ?, ?)
    """, (email, valor_formatado, forma_pagamento, status, codigo_transacao))

    conexao.commit()
    conexao.close()



# REGRAS DE NEGÓCIO E VALIDAÇÕES
# =========================================================================================================

def validar_pix(valor: float) -> tuple[float, str]:
    """Valida pagamento PIX, aplica 5% de desconto e gera o Copia e Cola."""
    if not isinstance(valor, (int, float)):
        raise ValueError("O valor da compra deve ser numérico.")
    
    if valor <= 0:
        raise ValueError("O valor da transação deve ser maior que R$ 0,00.")

    valor_final = round(valor * 0.95, 2)
    codigo_pix = f"00020126580014br.gov.bcb.pix-{uuid.uuid4()}"
    
    return valor_final, codigo_pix


def validar_cartao(numero_cartao: str, cvv: str, parcelas: int, valor: float) -> tuple[float, float, str]:
    """Valida número, CVV, parcelas e valor mínimo do cartão de crédito."""
    numero_limpo = str(numero_cartao).strip()
    cvv_limpo = str(cvv).strip()

    if not re.match(r"^\d{16}$", numero_limpo):
        raise ValueError("Número de cartão inválido. Deve conter exatamente 16 dígitos numéricos.")

    if not re.match(r"^\d{3,4}$", cvv_limpo):
        raise ValueError("CVV inválido. Deve conter 3 ou 4 dígitos numéricos.")

    if not (1 <= parcelas <= 12):
        raise ValueError("Quantidade de parcelas deve ser entre 1x e 12x.")

    valor_parcela = valor / parcelas
    if valor_parcela < 10.0:
        raise ValueError("O valor mínimo de cada parcela deve ser de R$ 10,00.")

    codigo_autorizacao = f"AUTH-{str(uuid.uuid4())[:8].upper()}"
    return round(valor, 2), round(valor_parcela, 2), codigo_autorizacao


def validar_boleto(valor: float) -> tuple[float, str]:
    """Valida pagamento por boleto e gera a linha digitável simulada."""
    if not isinstance(valor, (int, float)) or valor <= 0:
        raise ValueError("O valor do boleto deve ser maior que R$ 0,00.")

    linha_digitavel = f"34191.79001 {uuid.uuid4().int % 100000:.0f}.671234 5.890000000{int(valor)}"
    return round(valor, 2), linha_digitavel



# FLUXO PRINCIPAL (ORQUESTRADOR)
# =========================================================================================================

def processar_pagamento(email: str, forma_pagamento: str, valor: float, **dados_adicionais) -> dict:
    """Função principal que orquestra a validação e salva no banco de dados."""
    
    # Garante que a tabela exista antes de qualquer operação
    inicializar_banco_pagamentos()
    
    forma = forma_pagamento.strip().upper()

    if forma == "PIX":
        valor_final, codigo = validar_pix(valor)
        status = "Aprovado"

    elif forma == "CARTAO":
        numero_cartao = dados_adicionais.get("numero_cartao", "")
        cvv = dados_adicionais.get("cvv", "")
        parcelas = dados_adicionais.get("parcelas", 1)

        valor_final, _, codigo = validar_cartao(numero_cartao, cvv, parcelas, valor)
        status = "Aprovado"

    elif forma == "BOLETO":
        valor_final, codigo = validar_boleto(valor)
        status = "Pendente"

    else:
        raise ValueError("Forma de pagamento inválida. Escolha entre PIX, CARTAO ou BOLETO.")

    # Grava a transação validada no banco SQLite
    salvar_pagamento_no_banco(email, valor_final, forma, status, codigo)

    return {
        "sucesso": True,
        "email": email,
        "forma_pagamento": forma,
        "valor_final": valor_final,
        "status": status,
        "codigo_transacao": codigo
    }



# TESTES AUTOMÁTICOS (RODE O ARQUIVO DIRETO PARA TESTAR)
# =========================================================================================================
if __name__ == "__main__":
    try:
        print("--- TESTANDO PIX ---")
        res_pix = processar_pagamento("usuario@email.com", "PIX", 100.0)
        print("✅ PIX Processado:", res_pix)

        print("\n--- TESTANDO CARTÃO ---")
        res_cartao = processar_pagamento(
            "usuario@email.com", 
            "CARTAO", 
            120.0, 
            numero_cartao="1234567812345678", 
            cvv="123", 
            parcelas=2
        )
        print("✅ Cartão Processado:", res_cartao)

    except ValueError as err:
        print("❌ Erro capturado:", err)