"""Testes automatizados da camada de reconciliação matemática (src/reporting/reconciliation.py)."""

from decimal import Decimal

from src.analytics.commercial_analysis import gerar_analises_comerciais
from src.analytics.kpis import calcular_kpis_executivos
from src.data.cleaning import separar_vendas_e_inconsistencias
from src.data.validation import validar_vendas
from src.reporting.reconciliation import executar_reconciliacao


def _montar_cenario_base(dataframe_bruto_minimo):
    df = dataframe_bruto_minimo(
        [
            {"Data": "06/01/2026", "Pedido": "P-1", "Loja": "Online", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "3", "Preço Unitário": "89,90"},
            {"Data": "06/01/2026", "Pedido": "P-1", "Loja": "Online", "Produto": "Teclado", "Categoria": "Acessórios", "Quantidade": "1", "Preço Unitário": "249,90"},
            {"Data": "15/02/2026", "Pedido": "P-2", "Loja": "Centro", "Produto": "Monitor", "Categoria": "Informática", "Quantidade": "2", "Preço Unitário": "899,90"},
            {"Data": "31/02/2026", "Pedido": "P-3", "Loja": "Sul", "Produto": "Monitor", "Categoria": "Informática", "Quantidade": "1", "Preço Unitário": "899,90"},
        ]
    )
    ingestao = {
        "arquivos_aceitos": [{"arquivo": "teste.csv", "registros_lidos": 4}],
        "arquivos_rejeitados": [],
        "total_registros_recebidos": 4,
    }
    validacao = validar_vendas(df)
    vendas_validas, inconsistencias = separar_vendas_e_inconsistencias(
        validacao["dados_validados"]
    )
    kpis = calcular_kpis_executivos(vendas_validas, 4, len(inconsistencias))
    analises = gerar_analises_comerciais(vendas_validas)
    return ingestao, vendas_validas, inconsistencias, kpis, analises


def test_reconciliacao_aprovada_detecta_ruido_float_mas_mantem_zero_divergencia_decimal(
    dataframe_bruto_minimo,
):
    ingestao, vendas_validas, inconsistencias, kpis, analises = _montar_cenario_base(
        dataframe_bruto_minimo
    )

    rec = executar_reconciliacao(
        resultado_ingestao=ingestao,
        vendas_validas=vendas_validas,
        inconsistencias=inconsistencias,
        kpis=kpis,
        analises=analises,
    )

    assert rec["aprovada"] is True
    assert rec["total_verificacoes"] == 11
    assert rec["total_reprovadas"] == 0
    # 3 * 89.90 em float64 produz 269.70000000000005
    assert rec["comparacao_float_vs_decimal"]["linhas_com_ruido_float"] >= 1


def test_reconciliacao_falha_com_divergencia_de_um_centavo_na_agregacao_por_loja(
    dataframe_bruto_minimo,
):
    ingestao, vendas_validas, inconsistencias, kpis, analises = _montar_cenario_base(
        dataframe_bruto_minimo
    )

    # Adultera 1 centavo na análise por loja para provar tolerância zero
    analises["lojas"].loc[0, "Faturamento"] = (
        analises["lojas"].loc[0, "Faturamento"] + Decimal("0.01")
    )

    rec = executar_reconciliacao(
        resultado_ingestao=ingestao,
        vendas_validas=vendas_validas,
        inconsistencias=inconsistencias,
        kpis=kpis,
        analises=analises,
    )

    assert rec["aprovada"] is False
    mapa = {item["codigo"]: item for item in rec["verificacoes"]}
    assert mapa["REC-04"]["aprovada"] is False
    assert mapa["REC-04"]["diferenca"] == Decimal("0.01")


def test_reconciliacao_falha_quando_soma_validos_mais_rejeitados_diverge(
    dataframe_bruto_minimo,
):
    ingestao, vendas_validas, inconsistencias, kpis, analises = _montar_cenario_base(
        dataframe_bruto_minimo
    )
    ingestao["total_registros_recebidos"] = 5

    rec = executar_reconciliacao(
        resultado_ingestao=ingestao,
        vendas_validas=vendas_validas,
        inconsistencias=inconsistencias,
        kpis=kpis,
        analises=analises,
    )

    assert rec["aprovada"] is False
    mapa = {item["codigo"]: item for item in rec["verificacoes"]}
    assert mapa["REC-02"]["aprovada"] is False
