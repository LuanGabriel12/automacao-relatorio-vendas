"""Cálculo de indicadores executivos comerciais com precisão Decimal."""

from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from src.config import CASAS_DECIMAIS_MOEDA, CASAS_DECIMAIS_PERCENTUAL


def arredondar_decimal(valor, casas=CASAS_DECIMAIS_MOEDA):
    """Arredonda um Decimal com regra comercial HALF_UP apenas para exibição."""
    return valor.quantize(casas, rounding=ROUND_HALF_UP)


def calcular_kpis_executivos(
    vendas_validas,
    total_registros_recebidos,
    total_registros_rejeitados,
):
    """Calcula KPIs comerciais consolidados usando razão entre totais (sem média de médias).

    Não calcula lucro nem margem porque os dados de entrada não contêm custos.
    Trata com segurança o cenário de zero vendas válidas (sem ZeroDivisionError).
    """
    registros_validos = len(vendas_validas)

    if total_registros_recebidos > 0:
        taxa_rejeicao_pct = (
            Decimal(total_registros_rejeitados) * Decimal("100")
        ) / Decimal(total_registros_recebidos)
    else:
        taxa_rejeicao_pct = Decimal("0.00")

    if registros_validos == 0:
        faturamento_total = Decimal("0.00")
        quantidade_pedidos = 0
        unidades_vendidas = 0
        ticket_medio_pedido = Decimal("0.00")
        receita_por_unidade = Decimal("0.00")
        unidades_por_pedido = Decimal("0.00")
        registros_por_pedido = Decimal("0.00")
    else:
        faturamento_total = sum(vendas_validas["Faturamento"], Decimal("0.00"))
        quantidade_pedidos = int(vendas_validas["Pedido"].nunique())
        unidades_vendidas = sum((int(q) for q in vendas_validas["Quantidade"]), 0)

        ticket_medio_pedido = (
            faturamento_total / Decimal(quantidade_pedidos)
            if quantidade_pedidos > 0
            else Decimal("0.00")
        )
        receita_por_unidade = (
            faturamento_total / Decimal(unidades_vendidas)
            if unidades_vendidas > 0
            else Decimal("0.00")
        )
        unidades_por_pedido = (
            Decimal(unidades_vendidas) / Decimal(quantidade_pedidos)
            if quantidade_pedidos > 0
            else Decimal("0.00")
        )
        registros_por_pedido = (
            Decimal(registros_validos) / Decimal(quantidade_pedidos)
            if quantidade_pedidos > 0
            else Decimal("0.00")
        )

    return {
        "total_registros_recebidos": int(total_registros_recebidos),
        "registros_validos": int(registros_validos),
        "registros_rejeitados": int(total_registros_rejeitados),
        "taxa_rejeicao_pct": taxa_rejeicao_pct,
        "quantidade_pedidos": quantidade_pedidos,
        "unidades_vendidas": unidades_vendidas,
        "faturamento_total": faturamento_total,
        "ticket_medio_pedido": ticket_medio_pedido,
        "receita_por_unidade": receita_por_unidade,
        "unidades_por_pedido": unidades_por_pedido,
        "registros_por_pedido": registros_por_pedido,
    }


def construir_tabela_kpis_executivos(kpis):
    """Converte o dicionário de KPIs executivos em DataFrame estruturado para exportação."""
    linhas = [
        {
            "Indicador": "Total de registros recebidos (arquivos aceitos)",
            "Valor": kpis["total_registros_recebidos"],
            "Unidade": "registros",
            "Formula": "Soma de linhas lidas dos arquivos CSV aceitos",
        },
        {
            "Indicador": "Registros de vendas válidos",
            "Valor": kpis["registros_validos"],
            "Unidade": "registros",
            "Formula": "Linhas aprovadas em todas as regras de validação",
        },
        {
            "Indicador": "Registros rejeitados (inconsistências)",
            "Valor": kpis["registros_rejeitados"],
            "Unidade": "registros",
            "Formula": "Linhas com um ou mais motivos de inconsistência",
        },
        {
            "Indicador": "Taxa de registros rejeitados",
            "Valor": arredondar_decimal(
                kpis["taxa_rejeicao_pct"], CASAS_DECIMAIS_PERCENTUAL
            ),
            "Unidade": "%",
            "Formula": "(Registros rejeitados / Registros recebidos) * 100",
        },
        {
            "Indicador": "Quantidade de pedidos distintos",
            "Valor": kpis["quantidade_pedidos"],
            "Unidade": "pedidos",
            "Formula": "Contagem distinta de Pedido nas vendas válidas",
        },
        {
            "Indicador": "Quantidade de unidades vendidas",
            "Valor": kpis["unidades_vendidas"],
            "Unidade": "unidades",
            "Formula": "Soma da coluna Quantidade nas vendas válidas",
        },
        {
            "Indicador": "Faturamento total",
            "Valor": kpis["faturamento_total"],
            "Unidade": "R$",
            "Formula": "Soma de (Quantidade * Preço Unitário) em Decimal exato",
        },
        {
            "Indicador": "Ticket médio por pedido",
            "Valor": arredondar_decimal(kpis["ticket_medio_pedido"]),
            "Unidade": "R$/pedido",
            "Formula": "Faturamento total / Quantidade de pedidos distintos",
        },
        {
            "Indicador": "Receita por unidade",
            "Valor": arredondar_decimal(kpis["receita_por_unidade"]),
            "Unidade": "R$/unidade",
            "Formula": "Faturamento total / Quantidade de unidades vendidas",
        },
        {
            "Indicador": "Unidades médias por pedido",
            "Valor": arredondar_decimal(kpis["unidades_por_pedido"]),
            "Unidade": "unidades/pedido",
            "Formula": "Quantidade de unidades vendidas / Quantidade de pedidos distintos",
        },
        {
            "Indicador": "Itens (linhas) médios por pedido",
            "Valor": arredondar_decimal(kpis["registros_por_pedido"]),
            "Unidade": "linhas/pedido",
            "Formula": "Registros válidos / Quantidade de pedidos distintos",
        },
    ]
    return pd.DataFrame(linhas)
