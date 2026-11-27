"""Configurações centrais, caminhos e contratos de colunas do Sales Automation Engine V2."""

from decimal import Decimal
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_DADOS_ENTRADA = RAIZ_PROJETO / "dados" / "entrada"
PASTA_EXEMPLOS = RAIZ_PROJETO / "dados" / "exemplos"
PASTA_RESULTADO = RAIZ_PROJETO / "resultado"
PASTA_RELATORIOS = RAIZ_PROJETO / "reports"

COLUNAS_OBRIGATORIAS = [
    "Data",
    "Pedido",
    "Loja",
    "Produto",
    "Categoria",
    "Quantidade",
    "Preço Unitário",
]

COLUNAS_NEGOCIO_DUPLICATA = [
    "_data_dt",
    "_pedido",
    "_loja",
    "_produto",
    "_categoria",
    "_quantidade",
    "_preco_unitario",
]

SEPARADOR_CSV = ";"
CODIFICACAO_LEITURA = "utf-8-sig"
CODIFICACAO_ESCRITA = "utf-8"
TERMINADOR_LINHA = "\n"
FORMATO_DATA_BR = "%d/%m/%Y"

CASAS_DECIMAIS_MOEDA = Decimal("0.01")
CASAS_DECIMAIS_PERCENTUAL = Decimal("0.01")
TOLERANCIA_MONETARIA = Decimal("0.00")

STATUS_SUCESSO = "SUCESSO"
STATUS_CONCLUIDO_PARCIALMENTE = "CONCLUIDO_PARCIALMENTE"
STATUS_SEM_VENDAS_VALIDAS = "CONCLUIDO_SEM_VENDAS_VALIDAS"
STATUS_PARCIAL_SEM_VENDAS_VALIDAS = "CONCLUIDO_PARCIALMENTE_SEM_VENDAS_VALIDAS"
STATUS_FALHA = "FALHA"

ARQUIVOS_SAIDA = {
    "vendas_tratadas": "vendas_tratadas.csv",
    "inconsistencias": "inconsistencias.csv",
    "kpis_executivos": "kpis_executivos.csv",
    "analise_lojas": "analise_lojas.csv",
    "analise_produtos": "analise_produtos.csv",
    "analise_categorias": "analise_categorias.csv",
    "analise_mensal": "analise_mensal.csv",
    "relatorio_qualidade": "relatorio_qualidade.md",
    "relatorio_reconciliacao": "relatorio_reconciliacao.md",
    "relatorio_executivo": "relatorio_executivo.md",
    "resumo_execucao": "resumo_execucao.json",
}
