"""Testes automatizados da camada de qualidade e validação (src/data/validation.py)."""

from decimal import Decimal

from src.data.validation import (
    converter_preco_br,
    converter_quantidade_br,
    converter_texto_para_decimal_br,
    validar_vendas,
)


def test_conversao_decimal_br_direta_sem_float():
    assert converter_texto_para_decimal_br("3.499,90") == Decimal("3499.90")
    assert converter_texto_para_decimal_br("89,90") == Decimal("89.90")
    assert converter_texto_para_decimal_br("1.234.567,89") == Decimal("1234567.89")
    assert converter_texto_para_decimal_br("100") == Decimal("100")
    assert converter_texto_para_decimal_br("-2") == Decimal("-2")
    assert converter_texto_para_decimal_br("  0,50  ") == Decimal("0.50")


def test_conversao_rejeita_formatos_malformados_e_infinitos():
    invalidos = [
        "",
        "   ",
        "abc",
        "R$ 89,90",
        "12.34",       # ponto com 2 dígitos (formato americano, não milhar BR)
        "1..000",      # pontos consecutivos
        "01.000",      # zero à esquerda em grupo de milhar
        "1,2,3",       # múltiplas vírgulas
        ",50",         # parte inteira vazia
        "10,",         # parte decimal vazia
        "1_000",       # underscore Python
        "1e3",         # notação científica
        "inf",
        "-inf",
        "Infinity",
        "-Infinity",
        "NaN",
        "nan",
        "+10",
    ]
    for texto in invalidos:
        assert converter_preco_br(texto) is None, f"Deveria rejeitar '{texto}'"


def test_conversao_quantidade_exige_inteiro():
    assert converter_quantidade_br("5") == 5
    assert converter_quantidade_br("1.000") == 1000
    assert converter_quantidade_br("-2") == -2
    assert converter_quantidade_br("0") == 0

    for invalido in ["1,5", "2,0", "2.5", "inf", "NaN", "dez", ""]:
        assert converter_quantidade_br(invalido) is None, f"Deveria rejeitar '{invalido}'"


def test_validacao_registra_multiplos_problemas_sem_contar_linha_duas_vezes(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {"Pedido": "P-OK", "Quantidade": "2", "Preço Unitário": "50,00"},
            {
                "Data": "31/02/2026",
                "Pedido": "",
                "Loja": "",
                "Produto": "Mouse",
                "Categoria": "Acessórios",
                "Quantidade": "-3",
                "Preço Unitário": "inf",
            },
        ]
    )

    res = validar_vendas(df)
    validados = res["dados_validados"]

    assert res["total_registros_recebidos"] == 2
    assert res["total_registros_validos"] == 1
    assert res["total_registros_rejeitados"] == 1
    assert res["total_linhas_multiplos_erros"] == 1

    motivo_linha_erro = validados.loc[1, "Motivo"]
    assert "Data inválida" in motivo_linha_erro
    assert "Pedido ausente" in motivo_linha_erro
    assert "Loja ausente" in motivo_linha_erro
    assert "Quantidade inválida (menor ou igual a zero)" in motivo_linha_erro
    assert "Preço inválido (formato inválido ou não finito)" in motivo_linha_erro
    assert validados.loc[1, "Quantidade de problemas"] == 5


def test_validacao_rejeita_quantidade_fracionada_e_preco_malformado(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {"Pedido": "P-1", "Quantidade": "1,5", "Preço Unitário": "100,00"},
            {"Pedido": "P-2", "Quantidade": "2", "Preço Unitário": "12.34"},
            {"Pedido": "P-3", "Quantidade": "0", "Preço Unitário": "0,00"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 0
    assert res["total_registros_rejeitados"] == 3
    assert "formato não inteiro" in res["dados_validados"].loc[0, "Motivo"]
    assert "formato inválido" in res["dados_validados"].loc[1, "Motivo"]
    assert "Quantidade inválida (menor ou igual a zero)" in res["dados_validados"].loc[2, "Motivo"]
    assert "Preço inválido (menor ou igual a zero)" in res["dados_validados"].loc[2, "Motivo"]


def test_conflito_de_data_e_loja_no_mesmo_pedido_rejeita_todas_linhas_envolvidas(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {"Data": "05/01/2026", "Pedido": "P-CONF-DATA", "Loja": "Centro", "Produto": "A", "Arquivo de origem": "f1.csv"},
            {"Data": "06/01/2026", "Pedido": "P-CONF-DATA", "Loja": "Centro", "Produto": "B", "Arquivo de origem": "f2.csv"},
            {"Data": "08/01/2026", "Pedido": "P-CONF-LOJA", "Loja": "Online", "Produto": "A", "Arquivo de origem": "f1.csv"},
            {"Data": "08/01/2026", "Pedido": "P-CONF-LOJA", "Loja": "Sul", "Produto": "B", "Arquivo de origem": "f2.csv"},
            {"Data": "09/01/2026", "Pedido": "P-VALIDO", "Loja": "Norte", "Produto": "C", "Arquivo de origem": "f1.csv"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 1
    assert res["total_registros_rejeitados"] == 4
    assert res["pedidos_conflito_data"] == ["P-CONF-DATA"]
    assert res["pedidos_conflito_loja"] == ["P-CONF-LOJA"]

    validados = res["dados_validados"]
    assert validados.loc[0, "Status"] == "Inválido"
    assert validados.loc[1, "Status"] == "Inválido"
    assert "Data divergente" in validados.loc[0, "Motivo"]
    assert "Data divergente" in validados.loc[1, "Motivo"]
    assert "Loja divergente" in validados.loc[2, "Motivo"]
    assert "Loja divergente" in validados.loc[3, "Motivo"]
    assert validados.loc[4, "Status"] == "Válido"


def test_pedido_multiplos_itens_diferentes_e_valido(dataframe_bruto_minimo):
    df = dataframe_bruto_minimo(
        [
            {"Data": "10/01/2026", "Pedido": "P-MULTI", "Loja": "Centro", "Produto": "Notebook", "Categoria": "Informática", "Quantidade": "1", "Preço Unitário": "3.000,00"},
            {"Data": "10/01/2026", "Pedido": "P-MULTI", "Loja": "Centro", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "2", "Preço Unitário": "100,00"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 2
    assert res["total_registros_rejeitados"] == 0
    assert len(res["alertas_investigacao"]) == 0


def test_mesmo_pedido_e_produto_com_preco_ou_qtd_diferente_gera_alerta_mas_fica_valido(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {"Data": "10/01/2026", "Pedido": "P-LOTE", "Loja": "Online", "Produto": "SSD 1TB", "Categoria": "Componentes", "Quantidade": "1", "Preço Unitário": "450,00"},
            {"Data": "10/01/2026", "Pedido": "P-LOTE", "Loja": "Online", "Produto": "SSD 1TB", "Categoria": "Componentes", "Quantidade": "2", "Preço Unitário": "400,00"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 2
    assert res["total_registros_rejeitados"] == 0
    assert len(res["alertas_investigacao"]) == 1
    alerta = res["alertas_investigacao"][0]
    assert alerta["pedido"] == "P-LOTE"
    assert alerta["produto"] == "SSD 1TB"
    assert alerta["ocorrencias"] == 2


def test_duplicata_exata_normalizada_mantem_primeira_e_rejeita_segunda(
    dataframe_bruto_minimo,
):
    df = dataframe_bruto_minimo(
        [
            {"Data": "06/01/2026", "Pedido": "P-1002", "Loja": "Online", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "3", "Preço Unitário": "89,90"},
            {"Data": " 06/01/2026 ", "Pedido": " P-1002 ", "Loja": " Online ", "Produto": "Mouse", "Categoria": "Acessórios", "Quantidade": "3", "Preço Unitário": "89,9"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 1
    assert res["total_registros_rejeitados"] == 1
    assert res["dados_validados"].loc[0, "Status"] == "Válido"
    assert res["dados_validados"].loc[1, "Motivo"] == "Registro duplicado"


def test_precisao_inteiro_acima_limite_float64_misturado_com_invalido(
    dataframe_bruto_minimo,
):
    """Regressão: 9007199254740993 (2^53 + 1) junto com None não pode arredondar para 9007199254740992."""
    df = dataframe_bruto_minimo(
        [
            {"Pedido": "P-GRANDE", "Quantidade": "9007199254740993", "Preço Unitário": "10,00"},
            {"Pedido": "P-INV", "Quantidade": "abc", "Preço Unitário": "10,00"},
        ]
    )

    res = validar_vendas(df)
    assert res["total_registros_validos"] == 1
    assert res["total_registros_rejeitados"] == 1
    assert res["dados_validados"].loc[0, "_quantidade"] == 9007199254740993
    assert res["dados_validados"].loc[1, "_quantidade"] is None
