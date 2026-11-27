"""Análises comerciais agrupadas por loja, produto, categoria e período mensal."""

from decimal import Decimal

import pandas as pd


def _somar_faturamento_decimal(vendas_validas):
    """Soma a coluna Faturamento em Decimal exato."""
    if len(vendas_validas) == 0:
        return Decimal("0.00")
    return sum(vendas_validas["Faturamento"], Decimal("0.00"))


def _calcular_participacoes(faturamentos, faturamento_total):
    """Calcula participação percentual exata em Decimal para cada linha."""
    if faturamento_total <= Decimal("0"):
        return [Decimal("0.00") for _ in faturamentos]
    return [
        (valor * Decimal("100")) / faturamento_total
        for valor in faturamentos
    ]


def analisar_por_loja(vendas_validas):
    """Gera ranking e indicadores comerciais consolidados por loja."""
    colunas = [
        "Ranking",
        "Loja",
        "Registros",
        "Pedidos",
        "Quantidade",
        "Faturamento",
        "Ticket Médio",
        "Receita por Unidade",
        "Participação (%)",
    ]
    if len(vendas_validas) == 0:
        return pd.DataFrame(columns=colunas)

    faturamento_total = _somar_faturamento_decimal(vendas_validas)

    agrupado = (
        vendas_validas.groupby("Loja")
        .agg(
            Registros=("Pedido", "count"),
            Pedidos=("Pedido", "nunique"),
            Quantidade=("Quantidade", "sum"),
            Faturamento=("Faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            ["Faturamento", "Quantidade", "Loja"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )

    agrupado["Registros"] = agrupado["Registros"].astype(int)
    agrupado["Pedidos"] = agrupado["Pedidos"].astype(int)
    agrupado["Quantidade"] = pd.DataFrame(
        {"q": [int(v) for v in agrupado["Quantidade"]]}, dtype="object"
    )["q"]

    faturamentos = list(agrupado["Faturamento"])
    pedidos = list(agrupado["Pedidos"])
    quantidades = list(agrupado["Quantidade"])

    agrupado["Ticket Médio"] = [
        fat / Decimal(ped) if ped > 0 else Decimal("0.00")
        for fat, ped in zip(faturamentos, pedidos)
    ]
    agrupado["Receita por Unidade"] = [
        fat / Decimal(qtd) if qtd > 0 else Decimal("0.00")
        for fat, qtd in zip(faturamentos, quantidades)
    ]
    agrupado["Participação (%)"] = _calcular_participacoes(
        faturamentos, faturamento_total
    )
    agrupado["Ranking"] = list(range(1, len(agrupado) + 1))

    return agrupado.loc[:, colunas].copy()


def analisar_por_produto(vendas_validas):
    """Gera ranking e indicadores comerciais consolidados por produto e categoria."""
    colunas = [
        "Ranking",
        "Produto",
        "Categoria",
        "Registros",
        "Pedidos",
        "Quantidade",
        "Faturamento",
        "Receita por Unidade",
        "Participação (%)",
    ]
    if len(vendas_validas) == 0:
        return pd.DataFrame(columns=colunas)

    faturamento_total = _somar_faturamento_decimal(vendas_validas)

    agrupado = (
        vendas_validas.groupby(["Produto", "Categoria"])
        .agg(
            Registros=("Pedido", "count"),
            Pedidos=("Pedido", "nunique"),
            Quantidade=("Quantidade", "sum"),
            Faturamento=("Faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            ["Faturamento", "Quantidade", "Produto", "Categoria"],
            ascending=[False, False, True, True],
        )
        .reset_index(drop=True)
    )

    agrupado["Registros"] = agrupado["Registros"].astype(int)
    agrupado["Pedidos"] = agrupado["Pedidos"].astype(int)
    agrupado["Quantidade"] = pd.DataFrame(
        {"q": [int(v) for v in agrupado["Quantidade"]]}, dtype="object"
    )["q"]

    faturamentos = list(agrupado["Faturamento"])
    quantidades = list(agrupado["Quantidade"])

    agrupado["Receita por Unidade"] = [
        fat / Decimal(qtd) if qtd > 0 else Decimal("0.00")
        for fat, qtd in zip(faturamentos, quantidades)
    ]
    agrupado["Participação (%)"] = _calcular_participacoes(
        faturamentos, faturamento_total
    )
    agrupado["Ranking"] = list(range(1, len(agrupado) + 1))

    return agrupado.loc[:, colunas].copy()


def analisar_por_categoria(vendas_validas):
    """Gera ranking e participação percentual consolidada por categoria."""
    colunas = [
        "Ranking",
        "Categoria",
        "Registros",
        "Pedidos",
        "Produtos Distintos",
        "Quantidade",
        "Faturamento",
        "Receita por Unidade",
        "Participação (%)",
    ]
    if len(vendas_validas) == 0:
        return pd.DataFrame(columns=colunas)

    faturamento_total = _somar_faturamento_decimal(vendas_validas)

    agrupado = (
        vendas_validas.groupby("Categoria")
        .agg(
            Registros=("Pedido", "count"),
            Pedidos=("Pedido", "nunique"),
            **{"Produtos Distintos": ("Produto", "nunique")},
            Quantidade=("Quantidade", "sum"),
            Faturamento=("Faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            ["Faturamento", "Quantidade", "Categoria"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )

    agrupado["Registros"] = agrupado["Registros"].astype(int)
    agrupado["Pedidos"] = agrupado["Pedidos"].astype(int)
    agrupado["Produtos Distintos"] = agrupado["Produtos Distintos"].astype(int)
    agrupado["Quantidade"] = pd.DataFrame(
        {"q": [int(v) for v in agrupado["Quantidade"]]}, dtype="object"
    )["q"]

    faturamentos = list(agrupado["Faturamento"])
    quantidades = list(agrupado["Quantidade"])

    agrupado["Receita por Unidade"] = [
        fat / Decimal(qtd) if qtd > 0 else Decimal("0.00")
        for fat, qtd in zip(faturamentos, quantidades)
    ]
    agrupado["Participação (%)"] = _calcular_participacoes(
        faturamentos, faturamento_total
    )
    agrupado["Ranking"] = list(range(1, len(agrupado) + 1))

    return agrupado.loc[:, colunas].copy()


def analisar_mensal(vendas_validas):
    """Gera evolução mensal e comparação entre períodos consecutivos."""
    colunas = [
        "Ano_Mes",
        "Registros",
        "Pedidos",
        "Quantidade",
        "Faturamento",
        "Ticket Médio",
        "Receita por Unidade",
        "Participação (%)",
        "Faturamento Período Anterior",
        "Variação Faturamento (R$)",
        "Variação Faturamento (%)",
        "Variação Unidades (%)",
    ]
    if len(vendas_validas) == 0:
        return pd.DataFrame(columns=colunas)

    faturamento_total = _somar_faturamento_decimal(vendas_validas)

    agrupado = (
        vendas_validas.groupby("Ano_Mes")
        .agg(
            Registros=("Pedido", "count"),
            Pedidos=("Pedido", "nunique"),
            Quantidade=("Quantidade", "sum"),
            Faturamento=("Faturamento", "sum"),
        )
        .reset_index()
        .sort_values("Ano_Mes", ascending=True)
        .reset_index(drop=True)
    )

    agrupado["Registros"] = agrupado["Registros"].astype(int)
    agrupado["Pedidos"] = agrupado["Pedidos"].astype(int)
    agrupado["Quantidade"] = pd.DataFrame(
        {"q": [int(v) for v in agrupado["Quantidade"]]}, dtype="object"
    )["q"]

    faturamentos = list(agrupado["Faturamento"])
    pedidos = list(agrupado["Pedidos"])
    quantidades = list(agrupado["Quantidade"])

    agrupado["Ticket Médio"] = [
        fat / Decimal(ped) if ped > 0 else Decimal("0.00")
        for fat, ped in zip(faturamentos, pedidos)
    ]
    agrupado["Receita por Unidade"] = [
        fat / Decimal(qtd) if qtd > 0 else Decimal("0.00")
        for fat, qtd in zip(faturamentos, quantidades)
    ]
    agrupado["Participação (%)"] = _calcular_participacoes(
        faturamentos, faturamento_total
    )

    faturamento_anterior_lista = []
    variacao_abs_lista = []
    variacao_pct_lista = []
    variacao_unidades_pct_lista = []

    for indice in range(len(faturamentos)):
        if indice == 0:
            faturamento_anterior_lista.append(None)
            variacao_abs_lista.append(None)
            variacao_pct_lista.append(None)
            variacao_unidades_pct_lista.append(None)
        else:
            fat_anterior = faturamentos[indice - 1]
            fat_atual = faturamentos[indice]
            qtd_anterior = quantidades[indice - 1]
            qtd_atual = quantidades[indice]

            variacao_abs = fat_atual - fat_anterior
            variacao_pct = (
                (variacao_abs * Decimal("100")) / fat_anterior
                if fat_anterior > Decimal("0")
                else None
            )
            variacao_unid_pct = (
                (Decimal(qtd_atual - qtd_anterior) * Decimal("100"))
                / Decimal(qtd_anterior)
                if qtd_anterior > 0
                else None
            )

            faturamento_anterior_lista.append(fat_anterior)
            variacao_abs_lista.append(variacao_abs)
            variacao_pct_lista.append(variacao_pct)
            variacao_unidades_pct_lista.append(variacao_unid_pct)

    agrupado["Faturamento Período Anterior"] = faturamento_anterior_lista
    agrupado["Variação Faturamento (R$)"] = variacao_abs_lista
    agrupado["Variação Faturamento (%)"] = variacao_pct_lista
    agrupado["Variação Unidades (%)"] = variacao_unidades_pct_lista

    return agrupado.loc[:, colunas].copy()


def gerar_analises_comerciais(vendas_validas):
    """Executa todas as análises comerciais e retorna um dicionário de DataFrames."""
    return {
        "lojas": analisar_por_loja(vendas_validas),
        "produtos": analisar_por_produto(vendas_validas),
        "categorias": analisar_por_categoria(vendas_validas),
        "mensal": analisar_mensal(vendas_validas),
    }
