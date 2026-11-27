"""Camada de reconciliação matemática independente com precisão Decimal."""

from decimal import Decimal

from src.config import TOLERANCIA_MONETARIA


TOLERANCIA_PERCENTUAL_EXATO = Decimal("0.000001")


def _somar_coluna_decimal(tabela, nome_coluna):
    """Soma valores Decimal de uma coluna, retornando Decimal('0.00') se vazia."""
    if len(tabela) == 0:
        return Decimal("0.00")
    return sum(tabela[nome_coluna], Decimal("0.00"))


def _somar_coluna_int(tabela, nome_coluna):
    """Soma valores inteiros em precisão arbitrária do Python, retornando 0 se vazia."""
    if len(tabela) == 0:
        return 0
    return sum((int(v) for v in tabela[nome_coluna]), 0)


def _normalizar_zero_decimal(valor):
    """Evita notação científica '0E-25' em diferenças exatamente iguais a zero."""
    if isinstance(valor, Decimal) and valor == Decimal("0"):
        return Decimal("0.00")
    return valor


def _criar_verificacao(
    codigo,
    nome,
    formula,
    valor_esperado,
    valor_obtido,
    diferenca,
    aprovada,
):
    """Padroniza o registro de uma checagem matemática de reconciliação."""
    return {
        "codigo": codigo,
        "nome": nome,
        "formula": formula,
        "valor_esperado": _normalizar_zero_decimal(valor_esperado),
        "valor_obtido": _normalizar_zero_decimal(valor_obtido),
        "diferenca": _normalizar_zero_decimal(diferenca),
        "aprovada": bool(aprovada),
    }


def _comparar_float_vs_decimal(vendas_validas, faturamento_decimal):
    """Calcula a soma em float64 apenas para auditoria de ruído de ponto flutuante."""
    if len(vendas_validas) == 0:
        return {
            "faturamento_decimal": Decimal("0.00"),
            "faturamento_float_str": "0.0",
            "diferenca_float_vs_decimal": Decimal("0.00"),
            "linhas_com_ruido_float": 0,
        }

    soma_float = 0.0
    linhas_com_ruido = 0
    for qtd, preco, fat_dec in zip(
        vendas_validas["Quantidade"],
        vendas_validas["Preço Unitário"],
        vendas_validas["Faturamento"],
    ):
        try:
            fat_float = float(qtd) * float(preco)
            soma_float += fat_float
            if Decimal(str(fat_float)) != fat_dec:
                linhas_com_ruido += 1
        except (OverflowError, ValueError):
            linhas_com_ruido += 1

    try:
        faturamento_float_dec = Decimal(str(soma_float))
        diferenca = abs(faturamento_float_dec - faturamento_decimal)
    except Exception:
        diferenca = Decimal("0.00")
    return {
        "faturamento_decimal": faturamento_decimal,
        "faturamento_float_str": repr(soma_float),
        "diferenca_float_vs_decimal": diferenca,
        "linhas_com_ruido_float": linhas_com_ruido,
    }


def executar_reconciliacao(
    resultado_ingestao,
    vendas_validas,
    inconsistencias,
    kpis,
    analises,
):
    """Executa checagens independentes de contagem, faturamento, unidades, pedidos e KPIs.

    Todas as verificações monetárias utilizam ``Decimal`` exato (tolerância 0,00)
    para jamais mascarar divergências por arredondamento prematuro.
    """
    verificacoes = []

    # 1. Consistência entre arquivos aceitos e registros recebidos
    soma_linhas_arquivos_aceitos = sum(
        item["registros_lidos"] for item in resultado_ingestao["arquivos_aceitos"]
    )
    total_recebidos = int(resultado_ingestao["total_registros_recebidos"])
    diff_ingestao = total_recebidos - soma_linhas_arquivos_aceitos
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-01",
            nome="Registros consolidados vs. soma dos arquivos aceitos",
            formula="len(dados_brutos) == sum(registros_lidos nos arquivos aceitos)",
            valor_esperado=soma_linhas_arquivos_aceitos,
            valor_obtido=total_recebidos,
            diferenca=diff_ingestao,
            aprovada=(diff_ingestao == 0),
        )
    )

    # 2. Equação fundamental de registros: Recebidos = Válidos + Rejeitados
    soma_validos_rejeitados = len(vendas_validas) + len(inconsistencias)
    diff_registros = soma_validos_rejeitados - total_recebidos
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-02",
            nome="Equação fundamental de registros (Recebidos = Válidos + Rejeitados)",
            formula="total_registros_recebidos == len(vendas_validas) + len(inconsistencias)",
            valor_esperado=total_recebidos,
            valor_obtido=soma_validos_rejeitados,
            diferenca=diff_registros,
            aprovada=(diff_registros == 0),
        )
    )

    # 3. Faturamento consolidado recalculado de forma independente linha a linha
    faturamento_kpis = kpis["faturamento_total"]
    faturamento_recalculado = Decimal("0.00")
    for qtd, preco in zip(
        vendas_validas["Quantidade"], vendas_validas["Preço Unitário"]
    ):
        faturamento_recalculado += Decimal(int(qtd)) * preco

    diff_fat_recalc = abs(faturamento_recalculado - faturamento_kpis)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-03",
            nome="Faturamento consolidado (recálculo independente linha a linha)",
            formula="sum(Decimal(Quantidade) * Preço Unitário) == kpis['faturamento_total']",
            valor_esperado=faturamento_recalculado,
            valor_obtido=faturamento_kpis,
            diferenca=diff_fat_recalc,
            aprovada=(diff_fat_recalc <= TOLERANCIA_MONETARIA),
        )
    )

    # 4. Faturamento agregado por loja vs. consolidado
    fat_lojas = _somar_coluna_decimal(analises["lojas"], "Faturamento")
    diff_fat_lojas = abs(fat_lojas - faturamento_kpis)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-04",
            nome="Faturamento agrupado por loja vs. consolidado",
            formula="sum(analise_lojas['Faturamento']) == faturamento_total",
            valor_esperado=faturamento_kpis,
            valor_obtido=fat_lojas,
            diferenca=diff_fat_lojas,
            aprovada=(diff_fat_lojas <= TOLERANCIA_MONETARIA),
        )
    )

    # 5. Faturamento agregado por produto vs. consolidado
    fat_produtos = _somar_coluna_decimal(analises["produtos"], "Faturamento")
    diff_fat_produtos = abs(fat_produtos - faturamento_kpis)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-05",
            nome="Faturamento agrupado por produto vs. consolidado",
            formula="sum(analise_produtos['Faturamento']) == faturamento_total",
            valor_esperado=faturamento_kpis,
            valor_obtido=fat_produtos,
            diferenca=diff_fat_produtos,
            aprovada=(diff_fat_produtos <= TOLERANCIA_MONETARIA),
        )
    )

    # 6. Faturamento agregado por categoria vs. consolidado
    fat_categorias = _somar_coluna_decimal(analises["categorias"], "Faturamento")
    diff_fat_categorias = abs(fat_categorias - faturamento_kpis)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-06",
            nome="Faturamento agrupado por categoria vs. consolidado",
            formula="sum(analise_categorias['Faturamento']) == faturamento_total",
            valor_esperado=faturamento_kpis,
            valor_obtido=fat_categorias,
            diferenca=diff_fat_categorias,
            aprovada=(diff_fat_categorias <= TOLERANCIA_MONETARIA),
        )
    )

    # 7. Faturamento agregado por mês vs. consolidado
    fat_mensal = _somar_coluna_decimal(analises["mensal"], "Faturamento")
    diff_fat_mensal = abs(fat_mensal - faturamento_kpis)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-07",
            nome="Faturamento agrupado por mês vs. consolidado",
            formula="sum(analise_mensal['Faturamento']) == faturamento_total",
            valor_esperado=faturamento_kpis,
            valor_obtido=fat_mensal,
            diferenca=diff_fat_mensal,
            aprovada=(diff_fat_mensal <= TOLERANCIA_MONETARIA),
        )
    )

    # 8. Unidades vendidas (consolidado vs. loja, produto, categoria e mês)
    unidades_kpis = int(kpis["unidades_vendidas"])
    unidades_base = _somar_coluna_int(vendas_validas, "Quantidade")
    unidades_lojas = _somar_coluna_int(analises["lojas"], "Quantidade")
    unidades_produtos = _somar_coluna_int(analises["produtos"], "Quantidade")
    unidades_categorias = _somar_coluna_int(analises["categorias"], "Quantidade")
    unidades_mensal = _somar_coluna_int(analises["mensal"], "Quantidade")

    unidades_consistentes = (
        unidades_kpis == unidades_base
        and unidades_lojas == unidades_kpis
        and unidades_produtos == unidades_kpis
        and unidades_categorias == unidades_kpis
        and unidades_mensal == unidades_kpis
    )
    maior_diff_unidades = max(
        abs(unidades_base - unidades_kpis),
        abs(unidades_lojas - unidades_kpis),
        abs(unidades_produtos - unidades_kpis),
        abs(unidades_categorias - unidades_kpis),
        abs(unidades_mensal - unidades_kpis),
    )
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-08",
            nome="Unidades vendidas (base vs. loja, produto, categoria e mês)",
            formula="unidades_totais == sum(lojas) == sum(produtos) == sum(categorias) == sum(mensal)",
            valor_esperado=unidades_kpis,
            valor_obtido=unidades_lojas,
            diferenca=maior_diff_unidades,
            aprovada=unidades_consistentes,
        )
    )

    # 9. Pedidos distintos (base vs. loja e mês — aditivos sob premissa de Pedido único)
    pedidos_kpis = int(kpis["quantidade_pedidos"])
    pedidos_base = int(vendas_validas["Pedido"].nunique()) if len(vendas_validas) > 0 else 0
    pedidos_lojas = _somar_coluna_int(analises["lojas"], "Pedidos")
    pedidos_mensal = _somar_coluna_int(analises["mensal"], "Pedidos")

    pedidos_consistentes = (
        pedidos_kpis == pedidos_base
        and pedidos_lojas == pedidos_kpis
        and pedidos_mensal == pedidos_kpis
    )
    maior_diff_pedidos = max(
        abs(pedidos_base - pedidos_kpis),
        abs(pedidos_lojas - pedidos_kpis),
        abs(pedidos_mensal - pedidos_kpis),
    )
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-09",
            nome="Pedidos distintos (base vs. soma por loja e por mês)",
            formula="nunique(Pedido) == sum(lojas['Pedidos']) == sum(mensal['Pedidos'])",
            valor_esperado=pedidos_kpis,
            valor_obtido=pedidos_lojas,
            diferenca=maior_diff_pedidos,
            aprovada=pedidos_consistentes,
        )
    )

    # 10. Participação percentual soma 100% nas agregações quando há faturamento > 0
    if faturamento_kpis > Decimal("0"):
        soma_pct_lojas = _somar_coluna_decimal(analises["lojas"], "Participação (%)")
        soma_pct_produtos = _somar_coluna_decimal(analises["produtos"], "Participação (%)")
        soma_pct_categorias = _somar_coluna_decimal(analises["categorias"], "Participação (%)")
        soma_pct_mensal = _somar_coluna_decimal(analises["mensal"], "Participação (%)")

        maior_diff_pct = max(
            abs(soma_pct_lojas - Decimal("100")),
            abs(soma_pct_produtos - Decimal("100")),
            abs(soma_pct_categorias - Decimal("100")),
            abs(soma_pct_mensal - Decimal("100")),
        )
        verificacoes.append(
            _criar_verificacao(
                codigo="REC-10",
                nome="Soma das participações percentuais (lojas, produtos, categorias e meses)",
                formula="sum(Participação (%)) == 100% em todas as dimensões",
                valor_esperado=Decimal("100.00"),
                valor_obtido=soma_pct_lojas,
                diferenca=maior_diff_pct,
                aprovada=(maior_diff_pct <= TOLERANCIA_PERCENTUAL_EXATO),
            )
        )
    else:
        verificacoes.append(
            _criar_verificacao(
                codigo="REC-10",
                nome="Soma das participações percentuais (sem vendas válidas)",
                formula="Participações iguais a 0% quando faturamento_total == 0",
                valor_esperado=Decimal("0.00"),
                valor_obtido=Decimal("0.00"),
                diferenca=Decimal("0.00"),
                aprovada=True,
            )
        )

    # 11. Verificação independente de Ticket Médio e Receita por Unidade (razão entre totais)
    ticket_esperado = (
        faturamento_recalculado / Decimal(pedidos_base)
        if pedidos_base > 0
        else Decimal("0.00")
    )
    receita_unid_esperada = (
        faturamento_recalculado / Decimal(unidades_base)
        if unidades_base > 0
        else Decimal("0.00")
    )
    diff_ticket = abs(kpis["ticket_medio_pedido"] - ticket_esperado)
    diff_receita_unid = abs(kpis["receita_por_unidade"] - receita_unid_esperada)
    verificacoes.append(
        _criar_verificacao(
            codigo="REC-11",
            nome="Consistência de Ticket Médio e Receita por Unidade (razão entre totais)",
            formula="ticket_medio == faturamento / pedidos e receita_unid == faturamento / unidades",
            valor_esperado=ticket_esperado,
            valor_obtido=kpis["ticket_medio_pedido"],
            diferenca=max(diff_ticket, diff_receita_unid),
            aprovada=(
                diff_ticket <= TOLERANCIA_MONETARIA
                and diff_receita_unid <= TOLERANCIA_MONETARIA
            ),
        )
    )

    total_aprovadas = sum(1 for item in verificacoes if item["aprovada"])
    total_reprovadas = len(verificacoes) - total_aprovadas
    comparacao_float = _comparar_float_vs_decimal(vendas_validas, faturamento_kpis)

    return {
        "aprovada": (total_reprovadas == 0),
        "total_verificacoes": len(verificacoes),
        "total_aprovadas": total_aprovadas,
        "total_reprovadas": total_reprovadas,
        "arquivos_aceitos_qtd": len(resultado_ingestao["arquivos_aceitos"]),
        "arquivos_rejeitados_qtd": len(resultado_ingestao["arquivos_rejeitados"]),
        "verificacoes": verificacoes,
        "comparacao_float_vs_decimal": comparacao_float,
    }
