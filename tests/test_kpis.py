"""Testes automatizados de KPIs executivos e análises comerciais (referência manual)."""

from decimal import Decimal

import pytest

from src.analytics.commercial_analysis import gerar_analises_comerciais
from src.analytics.kpis import calcular_kpis_executivos, construir_tabela_kpis_executivos
from src.data.cleaning import separar_vendas_e_inconsistencias
from src.data.validation import validar_vendas


def test_kpis_e_agregacoes_com_pedido_multi_item_conferidos_manualmente(
    dataframe_bruto_minimo,
):
    """Referência calculada manualmente:
    - P-1 (Jan, Centro): 2x100,00 (Informática) + 1x50,00 (Acessórios) = 250,00 (3 un.)
    - P-2 (Fev, Sul):    3x30,00 (Acessórios) = 90,00 (3 un.)
    - Total válido: 3 linhas, 2 pedidos distintos, 6 unidades, R$ 340,00
    - Ticket médio = 340,00 / 2 = 170,00 (NÃO 340 / 3 linhas!)
    - Receita/unid = 340,00 / 6 = 56,6666...
    - Variação Fev vs Jan = 90,00 - 250,00 = -160,00 (-64,00%)
    """
    df = dataframe_bruto_minimo(
        [
            {"Data": "10/01/2026", "Pedido": "P-1", "Loja": "Centro", "Produto": "Monitor", "Categoria": "Informática", "Quantidade": "2", "Preço Unitário": "100,00"},
            {"Data": "10/01/2026", "Pedido": "P-1", "Loja": "Centro", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "1", "Preço Unitário": "50,00"},
            {"Data": "12/02/2026", "Pedido": "P-2", "Loja": "Sul", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "3", "Preço Unitário": "30,00"},
            {"Data": "31/02/2026", "Pedido": "P-ERR", "Loja": "Sul", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "1", "Preço Unitário": "30,00"},
        ]
    )

    validacao = validar_vendas(df)
    vendas_validas, _ = separar_vendas_e_inconsistencias(validacao["dados_validados"])

    kpis = calcular_kpis_executivos(
        vendas_validas=vendas_validas,
        total_registros_recebidos=4,
        total_registros_rejeitados=1,
    )

    assert kpis["registros_validos"] == 3
    assert kpis["quantidade_pedidos"] == 2
    assert kpis["unidades_vendidas"] == 6
    assert kpis["faturamento_total"] == Decimal("340.00")
    assert kpis["ticket_medio_pedido"] == Decimal("170.00")
    assert float(kpis["receita_por_unidade"]) == pytest.approx(340.0 / 6.0, rel=1e-9)
    assert kpis["taxa_rejeicao_pct"] == Decimal("25")

    tabela_kpis = construir_tabela_kpis_executivos(kpis)
    assert len(tabela_kpis) == 11

    analises = gerar_analises_comerciais(vendas_validas)

    # Lojas: Centro (250,00, rank 1) e Sul (90,00, rank 2)
    lojas = analises["lojas"]
    assert list(lojas["Loja"]) == ["Centro", "Sul"]
    assert list(lojas["Ranking"]) == [1, 2]
    assert list(lojas["Faturamento"]) == [Decimal("250.00"), Decimal("90.00")]
    assert list(lojas["Pedidos"]) == [1, 1]

    # Categorias: P-1 aparece em Informática E Acessórios (soma de pedidos = 1+2 = 3 > 2 pedidos distintos)
    categorias = analises["categorias"]
    assert list(categorias["Categoria"]) == ["Informática", "Acessórios"]
    assert list(categorias["Faturamento"]) == [Decimal("200.00"), Decimal("140.00")]
    assert list(categorias["Pedidos"]) == [1, 2]

    # Mensal e variação entre períodos
    mensal = analises["mensal"]
    assert list(mensal["Ano_Mes"]) == ["2026-01", "2026-02"]
    assert mensal.loc[0, "Variação Faturamento (R$)"] is None
    assert mensal.loc[1, "Variação Faturamento (R$)"] == Decimal("-160.00")
    assert mensal.loc[1, "Variação Faturamento (%)"] == Decimal("-64")
    assert mensal.loc[1, "Variação Unidades (%)"] == Decimal("0")


def test_kpis_e_analises_sem_vendas_validas_nao_geram_divisao_por_zero(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [{"Data": "31/02/2026", "Pedido": "P-1", "Quantidade": "-1", "Preço Unitário": "10,00"}]
    )
    validacao = validar_vendas(df)
    vendas_validas, _ = separar_vendas_e_inconsistencias(validacao["dados_validados"])

    kpis = calcular_kpis_executivos(vendas_validas, 1, 1)
    assert kpis["faturamento_total"] == Decimal("0.00")
    assert kpis["ticket_medio_pedido"] == Decimal("0.00")
    assert kpis["receita_por_unidade"] == Decimal("0.00")
    assert kpis["taxa_rejeicao_pct"] == Decimal("100")

    analises = gerar_analises_comerciais(vendas_validas)
    assert len(analises["lojas"]) == 0
    assert len(analises["produtos"]) == 0
    assert len(analises["categorias"]) == 0
    assert len(analises["mensal"]) == 0
