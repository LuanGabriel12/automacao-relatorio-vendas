"""Camada de limpeza, separação e cálculo do faturamento por linha em Decimal."""

from decimal import Decimal

import pandas as pd


COLUNAS_VENDAS_TRATADAS = [
    "Data",
    "Ano_Mes",
    "Pedido",
    "Loja",
    "Produto",
    "Categoria",
    "Quantidade",
    "Preço Unitário",
    "Faturamento",
    "Arquivo de origem",
    "Linha no arquivo",
]

COLUNAS_INCONSISTENCIAS = [
    "Data",
    "Pedido",
    "Loja",
    "Produto",
    "Categoria",
    "Quantidade",
    "Preço Unitário",
    "Arquivo de origem",
    "Linha no arquivo",
    "Quantidade de problemas",
    "Motivo",
    "Status",
]


def separar_vendas_e_inconsistencias(dados_validados):
    """Separa registros válidos (normalizados e tipados) das inconsistências (valores originais).

    - ``vendas_validas`` recebe valores normalizados, ``Quantidade`` inteira,
      ``Preço Unitário`` e ``Faturamento`` em ``Decimal`` exato, e ``Ano_Mes`` (``YYYY-MM``).
    - ``inconsistencias`` preserva exatamente os valores originais lidos dos CSVs
      para auditoria e correção na origem.
    """
    if len(dados_validados) == 0:
        vendas_vazias = pd.DataFrame(columns=COLUNAS_VENDAS_TRATADAS)
        inconsistencias_vazias = pd.DataFrame(columns=COLUNAS_INCONSISTENCIAS)
        return vendas_vazias, inconsistencias_vazias

    mascara_validas = dados_validados["Status"] == "Válido"
    mascara_invalidas = dados_validados["Status"] == "Inválido"

    brutas_validas = dados_validados.loc[mascara_validas].copy().reset_index(drop=True)
    brutas_invalidas = dados_validados.loc[mascara_invalidas].copy().reset_index(drop=True)

    if len(brutas_validas) > 0:
        quantidades = [int(q) for q in brutas_validas["_quantidade"]]
        precos = list(brutas_validas["_preco_unitario"])
        faturamentos = [
            Decimal(qtd) * preco for qtd, preco in zip(quantidades, precos)
        ]

        vendas_validas = (
            pd.DataFrame(
                {
                    "Data": brutas_validas["_data_dt"],
                    "Ano_Mes": brutas_validas["_data_dt"].dt.to_period("M").astype(str),
                    "Pedido": brutas_validas["_pedido"],
                    "Loja": brutas_validas["_loja"],
                    "Produto": brutas_validas["_produto"],
                    "Categoria": brutas_validas["_categoria"],
                    "Quantidade": pd.DataFrame({"q": quantidades}, dtype="object")["q"],
                    "Preço Unitário": pd.DataFrame({"p": precos}, dtype="object")["p"],
                    "Faturamento": pd.DataFrame({"f": faturamentos}, dtype="object")["f"],
                    "Arquivo de origem": brutas_validas["Arquivo de origem"],
                    "Linha no arquivo": brutas_validas["Linha no arquivo"].astype(int),
                }
            )
            .sort_values(
                ["Data", "Pedido", "Produto", "Arquivo de origem", "Linha no arquivo"],
                ascending=[True, True, True, True, True],
            )
            .reset_index(drop=True)
        )
    else:
        vendas_validas = pd.DataFrame(columns=COLUNAS_VENDAS_TRATADAS)

    if len(brutas_invalidas) > 0:
        inconsistencias = (
            brutas_invalidas.loc[:, COLUNAS_INCONSISTENCIAS]
            .copy()
            .sort_values(["Arquivo de origem", "Linha no arquivo"], ascending=[True, True])
            .reset_index(drop=True)
        )
    else:
        inconsistencias = pd.DataFrame(columns=COLUNAS_INCONSISTENCIAS)

    return vendas_validas, inconsistencias
