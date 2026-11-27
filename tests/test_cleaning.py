"""Testes automatizados da camada de limpeza e separação (src/data/cleaning.py)."""

from decimal import Decimal

from src.data.cleaning import separar_vendas_e_inconsistencias
from src.data.validation import validar_vendas


def test_limpeza_normaliza_validas_calcula_decimal_exato_e_preserva_originais_nas_inconsistencias(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {
                "Data": " 06/01/2026 ",
                "Pedido": " P-1002 ",
                "Loja": " Online ",
                "Produto": " Mouse Sem Fio ",
                "Categoria": " Acessórios ",
                "Quantidade": "3",
                "Preço Unitário": "89,90",
            },
            {
                "Data": "31/02/2026",
                "Pedido": "P-ERR",
                "Loja": "Centro",
                "Produto": "Monitor 24",
                "Categoria": "Informática",
                "Quantidade": "1,5",
                "Preço Unitário": "inf",
            },
        ]
    )

    validacao = validar_vendas(df)
    vendas_validas, inconsistencias = separar_vendas_e_inconsistencias(
        validacao["dados_validados"]
    )

    assert len(vendas_validas) == 1
    assert len(inconsistencias) == 1

    # Normalização e precisão Decimal exata (sem 269.70000000000005)
    assert vendas_validas.loc[0, "Loja"] == "Online"
    assert vendas_validas.loc[0, "Pedido"] == "P-1002"
    assert vendas_validas.loc[0, "Ano_Mes"] == "2026-01"
    assert vendas_validas.loc[0, "Quantidade"] == 3
    assert vendas_validas.loc[0, "Preço Unitário"] == Decimal("89.90")
    assert vendas_validas.loc[0, "Faturamento"] == Decimal("269.70")

    # Valores originais preservados intactos na tabela de inconsistências
    assert inconsistencias.loc[0, "Data"] == "31/02/2026"
    assert inconsistencias.loc[0, "Quantidade"] == "1,5"
    assert inconsistencias.loc[0, "Preço Unitário"] == "inf"
    assert inconsistencias.loc[0, "Status"] == "Inválido"


def test_limpeza_com_zero_vendas_validas_mantem_esquema_de_colunas(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [{"Data": "31/02/2026", "Pedido": "P-1", "Quantidade": "-1", "Preço Unitário": "10,00"}]
    )
    validacao = validar_vendas(df)
    vendas_validas, inconsistencias = separar_vendas_e_inconsistencias(
        validacao["dados_validados"]
    )

    assert len(vendas_validas) == 0
    assert "Faturamento" in vendas_validas.columns
    assert "Ano_Mes" in vendas_validas.columns
    assert len(inconsistencias) == 1
