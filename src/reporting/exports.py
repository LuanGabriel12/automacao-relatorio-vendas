"""Exportação segura de CSVs (padrão brasileiro/Power BI), relatórios Markdown e JSON."""

from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

import pandas as pd

from src.config import (
    ARQUIVOS_SAIDA,
    CASAS_DECIMAIS_MOEDA,
    CASAS_DECIMAIS_PERCENTUAL,
    CODIFICACAO_ESCRITA,
    FORMATO_DATA_BR,
    SEPARADOR_CSV,
    STATUS_CONCLUIDO_PARCIALMENTE,
    STATUS_PARCIAL_SEM_VENDAS_VALIDAS,
    STATUS_SEM_VENDAS_VALIDAS,
    STATUS_SUCESSO,
    TERMINADOR_LINHA,
)


def formatar_numero_br(valor, casas=2):
    """Formata um número Decimal ou inteiro no padrão brasileiro (milhar '.' e decimal ',')."""
    if valor is None:
        return "N/A"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")

    quantizador = Decimal("1") if casas == 0 else Decimal("1." + ("0" * casas))
    arredondado = Decimal(valor).quantize(quantizador, rounding=ROUND_HALF_UP)
    texto = f"{arredondado:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_moeda_br(valor):
    """Formata um valor monetário Decimal em Reais (ex.: R$ 65.068,00)."""
    if valor is None:
        return "N/A"
    return f"R$ {formatar_numero_br(valor, casas=2)}"


def formatar_percentual_br(valor):
    """Formata um valor percentual Decimal com duas casas decimais (ex.: 14,29%)."""
    if valor is None:
        return "N/A"
    return f"{formatar_numero_br(valor, casas=2)}%"


def formatar_decimal_csv_exato(valor):
    """Formata Decimal para CSV brasileiro (vírgula decimal, sem ponto de milhar).

    Mantém no mínimo 2 casas decimais e preserva todas as casas caso o valor
    tenha mais de 2 dígitos decimais exatos (sem truncamento silencioso).
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, int):
        return str(valor)

    dec = Decimal(valor)
    expoente = dec.as_tuple().exponent
    if isinstance(expoente, int) and expoente > -2:
        dec = dec.quantize(CASAS_DECIMAIS_MOEDA, rounding=ROUND_HALF_UP)
    return str(dec).replace(".", ",")


def formatar_decimal_csv_arredondado(valor, casas=CASAS_DECIMAIS_MOEDA):
    """Formata Decimal arredondado para CSV brasileiro (ex.: indicadores derivados)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, int):
        return str(valor)
    arredondado = Decimal(valor).quantize(casas, rounding=ROUND_HALF_UP)
    return str(arredondado).replace(".", ",")


def _escapar_celula_markdown(valor):
    """Escapa caracteres que podem quebrar tabelas Markdown."""
    texto = str(valor)
    return texto.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _escrever_texto_atomico(caminho_final, conteudo):
    """Grava arquivo texto em temporário e substitui atomicamente o destino."""
    caminho = Path(caminho_final)
    caminho_tmp = caminho.with_name(caminho.name + ".tmp")
    caminho_tmp.write_text(conteudo, encoding=CODIFICACAO_ESCRITA, newline=TERMINADOR_LINHA)
    caminho_tmp.replace(caminho)


def _preparar_csv_texto(df):
    """Serializa DataFrame para string CSV UTF-8 com ';' e LF canônico."""
    return df.to_csv(
        sep=SEPARADOR_CSV,
        index=False,
        lineterminator=TERMINADOR_LINHA,
    )


def _preparar_vendas_para_csv(vendas_validas):
    """Prepara vendas_tratadas para CSV brasileiro compatível com Power BI."""
    saida = vendas_validas.copy()
    if len(saida) > 0:
        saida["Data"] = saida["Data"].dt.strftime(FORMATO_DATA_BR)
        saida["Preço Unitário"] = [
            formatar_decimal_csv_exato(v) for v in saida["Preço Unitário"]
        ]
        saida["Faturamento"] = [
            formatar_decimal_csv_exato(v) for v in saida["Faturamento"]
        ]
    return saida


def _preparar_kpis_para_csv(tabela_kpis):
    """Prepara tabela de KPIs executivos para CSV brasileiro."""
    saida = tabela_kpis.copy()
    valores_formatados = []
    for valor in saida["Valor"]:
        if isinstance(valor, Decimal):
            valores_formatados.append(formatar_decimal_csv_exato(valor))
        else:
            valores_formatados.append(str(valor))
    saida["Valor"] = valores_formatados
    return saida


def _preparar_analise_para_csv(df, colunas_exatas, colunas_arredondadas):
    """Formata colunas Decimal exatas e derivadas de uma tabela analítica para CSV."""
    saida = df.copy()
    if len(saida) == 0:
        return saida

    for coluna in colunas_exatas:
        if coluna in saida.columns:
            saida[coluna] = [formatar_decimal_csv_exato(v) for v in saida[coluna]]

    for coluna in colunas_arredondadas:
        if coluna in saida.columns:
            saida[coluna] = [
                formatar_decimal_csv_arredondado(v, CASAS_DECIMAIS_PERCENTUAL)
                for v in saida[coluna]
            ]
    return saida


def _descricao_status(status_execucao):
    """Retorna descrição humana honesta do status da execução."""
    descricoes = {
        STATUS_SUCESSO: "SUCESSO — Todos os arquivos foram aceitos, validados e reconciliados.",
        STATUS_CONCLUIDO_PARCIALMENTE: (
            "CONCLUÍDO PARCIALMENTE — Execução reconciliada sobre os arquivos aceitos, "
            "porém houve arquivos rejeitados integralmente (NÃO representa sucesso integral)."
        ),
        STATUS_SEM_VENDAS_VALIDAS: (
            "CONCLUÍDO SEM VENDAS VÁLIDAS — Todos os arquivos foram aceitos, "
            "mas nenhum registro passou na validação de qualidade."
        ),
        STATUS_PARCIAL_SEM_VENDAS_VALIDAS: (
            "CONCLUÍDO PARCIALMENTE SEM VENDAS VÁLIDAS — Houve arquivos rejeitados "
            "integralmente e nenhum registro válido restou após a validação."
        ),
    }
    return descricoes.get(status_execucao, status_execucao)


def gerar_relatorio_qualidade_md(
    timestamp_execucao,
    status_execucao,
    resultado_ingestao,
    resultado_validacao,
):
    """Gera o relatório Markdown de qualidade de dados e ingestão."""
    linhas = [
        "# Relatório de Qualidade dos Dados — Sales Automation Engine V2",
        "",
        f"- **Data/hora da execução:** {timestamp_execucao}",
        f"- **Pasta de entrada:** `{resultado_ingestao['pasta_entrada']}`",
        f"- **Status da execução:** `{status_execucao}`",
        f"- **Diagnóstico:** {_descricao_status(status_execucao)}",
        "",
    ]

    if len(resultado_ingestao["arquivos_rejeitados"]) > 0:
        linhas.extend(
            [
                "> **Atenção — Processamento Parcial:** Um ou mais arquivos da pasta de entrada foram rejeitados integralmente antes da consolidação. Os indicadores abaixo refletem apenas os arquivos aceitos.",
                "",
            ]
        )

    linhas.extend(
        [
            "## 1. Resumo da Ingestão de Arquivos",
            "",
            "| Métrica de Ingestão | Valor |",
            "| --- | ---: |",
            f"| Arquivos CSV encontrados | {resultado_ingestao['total_arquivos_encontrados']} |",
            f"| Arquivos aceitos | {len(resultado_ingestao['arquivos_aceitos'])} |",
            f"| Arquivos rejeitados integralmente | {len(resultado_ingestao['arquivos_rejeitados'])} |",
            f"| Total de registros recebidos (arquivos aceitos) | {formatar_numero_br(resultado_ingestao['total_registros_recebidos'], 0)} |",
            "",
            "### 1.1 Arquivos Aceitos",
            "",
            "| Arquivo | Registros Lidos | Colunas Extras Ignoradas |",
            "| --- | ---: | --- |",
        ]
    )

    for item in resultado_ingestao["arquivos_aceitos"]:
        extras = ", ".join(item["colunas_extras_ignoradas"]) or "Nenhuma"
        linhas.append(
            f"| `{_escapar_celula_markdown(item['arquivo'])}` | "
            f"{formatar_numero_br(item['registros_lidos'], 0)} | "
            f"{_escapar_celula_markdown(extras)} |"
        )

    linhas.extend(["", "### 1.2 Arquivos Rejeitados Integralmente", ""])
    if len(resultado_ingestao["arquivos_rejeitados"]) == 0:
        linhas.append("Nenhum arquivo foi rejeitado integralmente nesta execução.")
    else:
        linhas.extend(["| Arquivo | Motivo da Rejeição |", "| --- | --- |"])
        for item in resultado_ingestao["arquivos_rejeitados"]:
            linhas.append(
                f"| `{_escapar_celula_markdown(item['arquivo'])}` | "
                f"{_escapar_celula_markdown(item['motivo'])} |"
            )

    linhas.extend(
        [
            "",
            "## 2. Resumo da Validação de Registros",
            "",
            "| Indicador de Qualidade | Valor |",
            "| --- | ---: |",
            f"| Total de registros recebidos (arquivos aceitos) | {formatar_numero_br(resultado_validacao['total_registros_recebidos'], 0)} |",
            f"| Registros válidos | {formatar_numero_br(resultado_validacao['total_registros_validos'], 0)} |",
            f"| Registros rejeitados (inconsistências) | {formatar_numero_br(resultado_validacao['total_registros_rejeitados'], 0)} |",
            f"| Linhas com múltiplos problemas simultâneos | {formatar_numero_br(resultado_validacao['total_linhas_multiplos_erros'], 0)} |",
            f"| Taxa de registros rejeitados | {formatar_percentual_br(resultado_validacao['taxa_rejeicao_pct'])} |",
            f"| Alertas de investigação (`Pedido + Produto` recorrente) | {formatar_numero_br(len(resultado_validacao['alertas_investigacao']), 0)} |",
            "",
            "## 3. Distribuição de Motivos de Inconsistência",
            "",
        ]
    )

    contagem_motivos = resultado_validacao["contagem_motivos"]
    if len(contagem_motivos) == 0:
        linhas.append("Nenhuma inconsistência foi encontrada nos registros recebidos.")
    else:
        linhas.extend(
            [
                "| Motivo | Ocorrências |",
                "| --- | ---: |",
            ]
        )
        motivos_ordenados = sorted(
            contagem_motivos.items(),
            key=lambda par: (-par[1], par[0]),
        )
        for motivo, quantidade in motivos_ordenados:
            linhas.append(
                f"| {_escapar_celula_markdown(motivo)} | "
                f"{formatar_numero_br(quantidade, 0)} |"
            )
        linhas.extend(
            [
                "",
                "> **Nota de contagem:** Quando uma linha possui múltiplos erros simultâneos, todos os motivos são registrados na tabela acima e concatenados em `inconsistencias.csv`, mas a linha é contabilizada **uma única vez** no total de registros rejeitados e na reconciliação.",
            ]
        )

    linhas.extend(
        [
            "",
            "## 4. Conflitos de Cabeçalho de Pedido (`Data` / `Loja`)",
            "",
            "- **Premissa adotada:** o identificador `Pedido` é considerado globalmente único em toda a base recebida. Portanto, um mesmo pedido não pode apresentar datas ou lojas divergentes entre linhas ou arquivos; quando isso ocorre, **todas** as linhas envolvidas são rejeitadas.",
            f"- **Pedidos com conflito de Data:** {', '.join(resultado_validacao['pedidos_conflito_data']) if resultado_validacao['pedidos_conflito_data'] else 'Nenhum'}",
            f"- **Pedidos com conflito de Loja:** {', '.join(resultado_validacao['pedidos_conflito_loja']) if resultado_validacao['pedidos_conflito_loja'] else 'Nenhum'}",
            "",
            "## 5. Alertas de Investigação (`Pedido + Produto` com Atributos Distintos)",
            "",
            "Por decisão de negócio, linhas válidas com mesmo `Pedido` e mesmo `Produto`, porém com preço, quantidade ou categoria distintos, **não** são rejeitadas automaticamente, pois podem representar itens legítimos de um mesmo pedido na ausência de um identificador único de linha (`ID_Item`). Elas são destacadas abaixo para revisão humana:",
            "",
        ]
    )

    alertas = resultado_validacao["alertas_investigacao"]
    if len(alertas) == 0:
        linhas.append("Nenhum alerta de investigação identificado nesta execução.")
    else:
        linhas.extend(
            [
                "| Pedido | Produto | Ocorrências | Quantidades | Preços | Categorias | Arquivos |",
                "| --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for alerta in alertas[:50]:
            linhas.append(
                f"| `{_escapar_celula_markdown(alerta['pedido'])}` | "
                f"{_escapar_celula_markdown(alerta['produto'])} | "
                f"{alerta['ocorrencias']} | "
                f"{', '.join(str(q) for q in alerta['quantidades_encontradas'])} | "
                f"{', '.join(alerta['precos_encontrados'])} | "
                f"{', '.join(_escapar_celula_markdown(c) for c in alerta['categorias_encontradas'])} | "
                f"{', '.join(_escapar_celula_markdown(a) for a in alerta['arquivos_origem'])} |"
            )
        if len(alertas) > 50:
            linhas.append("")
            linhas.append(
                f"*Exibindo os primeiros 50 de {len(alertas)} alertas identificados.*"
            )

    linhas.extend(
        [
            "",
            "## 6. Política de Duplicatas e Limitação de Granularidade",
            "",
            "- **Pedidos com múltiplos itens:** um mesmo `Pedido` com produtos diferentes, mesma `Data` e mesma `Loja` é tratado como venda legítima de múltiplos itens e contabilizado como **1 pedido distinto**.",
            "- **Duplicatas exatas (política preservada da V1):** linhas integralmente idênticas nas 7 colunas de negócio normalizadas têm a primeira ocorrência mantida e as repetições seguintes rejeitadas como `Registro duplicado`.",
            "- **Limitação documentada:** como os arquivos de entrada não possuem chave única de linha (`ID_Item`), a remoção de duplicatas exatas é uma regra operacional adotada para este conjunto de dados e não uma garantia universal de que duas compras idênticas nunca ocorreriam no mesmo pedido.",
            "",
        ]
    )

    return "\n".join(linhas)


def _formatar_valor_reconciliacao(valor):
    """Formata valores heterogêneos (int ou Decimal) para tabela de reconciliação."""
    if isinstance(valor, Decimal):
        if valor == Decimal("0"):
            return "0,00"
        texto = format(valor.normalize(), "f")
        if "." in texto:
            inteira, frac = texto.split(".")
            if len(frac) < 2:
                frac = frac.ljust(2, "0")
            elif len(frac) > 6:
                frac = frac[:6]
            return f"{inteira},{frac}"
        return f"{texto},00"
    return formatar_numero_br(valor, 0)


def gerar_relatorio_reconciliacao_md(
    timestamp_execucao,
    status_execucao,
    resultado_reconciliacao,
):
    """Gera o relatório Markdown independente de reconciliação matemática."""
    veredito = "APROVADA" if resultado_reconciliacao["aprovada"] else "REPROVADA"
    comparacao = resultado_reconciliacao["comparacao_float_vs_decimal"]

    linhas = [
        "# Relatório de Reconciliação Matemática — Sales Automation Engine V2",
        "",
        f"- **Data/hora da execução:** {timestamp_execucao}",
        f"- **Status da execução:** `{status_execucao}`",
        f"- **Veredito da reconciliação:** **{veredito}** ({resultado_reconciliacao['total_aprovadas']}/{resultado_reconciliacao['total_verificacoes']} verificações aprovadas)",
        f"- **Escopo dos registros reconciliados:** apenas os `{resultado_reconciliacao['arquivos_aceitos_qtd']}` arquivo(s) aceito(s). Arquivos rejeitados integralmente (`{resultado_reconciliacao['arquivos_rejeitados_qtd']}`) são contabilizados separadamente para evitar distorção nas contagens de linhas.",
        "",
        "## 1. Matriz de Verificações Matemáticas",
        "",
        "| Código | Verificação | Fórmula | Esperado | Obtido | Diferença | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for item in resultado_reconciliacao["verificacoes"]:
        status_item = "APROVADA" if item["aprovada"] else "REPROVADA"
        linhas.append(
            f"| `{item['codigo']}` | "
            f"{_escapar_celula_markdown(item['nome'])} | "
            f"`{_escapar_celula_markdown(item['formula'])}` | "
            f"{_formatar_valor_reconciliacao(item['valor_esperado'])} | "
            f"{_formatar_valor_reconciliacao(item['valor_obtido'])} | "
            f"{_formatar_valor_reconciliacao(item['diferenca'])} | "
            f"**{status_item}** |"
        )

    linhas.extend(
        [
            "",
            "## 2. Auditoria de Precisão Monetária (`Decimal` vs. `float64`)",
            "",
            "Todos os valores monetários da V2 são construídos diretamente em `Decimal` a partir das strings normalizadas dos CSVs, sem conversão intermediária para `float`, garantindo tolerância zero (`0,00`) na reconciliação.",
            "",
            "| Critério de Precisão | Resultado Observado |",
            "| --- | --- |",
            f"| Faturamento consolidado em `Decimal` exato | `{formatar_moeda_br(comparacao['faturamento_decimal'])}` (`{comparacao['faturamento_decimal']}`) |",
            f"| Soma equivalente em `float64` (apenas auditoria) | `{comparacao['faturamento_float_str']}` |",
            f"| Diferença absoluta `float64` vs. `Decimal` no total | `{format(comparacao['diferenca_float_vs_decimal'].normalize(), 'f') if comparacao['diferenca_float_vs_decimal'] != Decimal('0') else '0.00'}` |",
            f"| Linhas com ruído binário em `float64` (`Qtd * Preço`) | `{comparacao['linhas_com_ruido_float']}` |",
            "",
            "## 3. Nota sobre Aditividade de Pedidos nas Agregações",
            "",
            "- **Por Loja e por Mês (`REC-09`):** a soma de `Pedidos` é aditiva e igual ao total de pedidos distintos, pois a regra de unicidade global de `Pedido` impede que um mesmo pedido exista em duas lojas ou duas datas distintas.",
            "- **Por Produto e por Categoria:** em pedidos com múltiplos itens de produtos/categorias diferentes, o mesmo `Pedido` aparece legitimamente em mais de um produto ou categoria; por isso, a contagem de `Pedidos` nessas duas dimensões **não** é somável ao total consolidado.",
            "",
        ]
    )

    return "\n".join(linhas)


def gerar_relatorio_executivo_md(
    timestamp_execucao,
    status_execucao,
    resultado_ingestao,
    resultado_validacao,
    kpis,
    analises,
    resultado_reconciliacao,
):
    """Gera o relatório executivo comercial com interpretação baseada somente nos dados."""
    linhas = [
        "# Relatório Executivo Comercial — Sales Automation Engine V2",
        "",
        f"- **Data/hora da execução:** {timestamp_execucao}",
        f"- **Status da execução:** `{status_execucao}`",
        f"- **Reconciliação matemática:** {'APROVADA' if resultado_reconciliacao['aprovada'] else 'REPROVADA'} ({resultado_reconciliacao['total_aprovadas']}/{resultado_reconciliacao['total_verificacoes']})",
        f"- **Arquivos processados:** {len(resultado_ingestao['arquivos_aceitos'])} aceito(s) / {len(resultado_ingestao['arquivos_rejeitados'])} rejeitado(s)",
        "",
        "> **Escopo:** Relatório gerado automaticamente sobre os arquivos de entrada fornecidos. Não apresenta lucro ou margem comercial porque a base não inclui dados de custo.",
        "",
    ]

    if len(resultado_ingestao["arquivos_rejeitados"]) > 0:
        linhas.extend(
            [
                "> **Alerta de Execução Parcial:** Existem arquivos rejeitados integralmente nesta execução (consulte `relatorio_qualidade.md`). Os resultados comerciais abaixo cobrem exclusivamente os arquivos aceitos.",
                "",
            ]
        )

    linhas.extend(
        [
            "## 1. KPIs Executivos Consolidados",
            "",
            "| Indicador | Valor | Fórmula / Critério |",
            "| --- | ---: | --- |",
            f"| **Faturamento Total** | **{formatar_moeda_br(kpis['faturamento_total'])}** | Soma de `Quantidade * Preço Unitário` (`Decimal`) |",
            f"| **Pedidos Distintos** | **{formatar_numero_br(kpis['quantidade_pedidos'], 0)}** | Contagem distinta de `Pedido` válido |",
            f"| **Unidades Vendidas** | **{formatar_numero_br(kpis['unidades_vendidas'], 0)}** | Soma de `Quantidade` nas vendas válidas |",
            f"| **Ticket Médio por Pedido** | **{formatar_moeda_br(kpis['ticket_medio_pedido'])}** | `Faturamento Total / Pedidos Distintos` |",
            f"| **Receita por Unidade** | **{formatar_moeda_br(kpis['receita_por_unidade'])}** | `Faturamento Total / Unidades Vendidas` |",
            f"| **Registros Válidos** | {formatar_numero_br(kpis['registros_validos'], 0)} | Linhas válidas (de {formatar_numero_br(kpis['total_registros_recebidos'], 0)} recebidas) |",
            f"| **Taxa de Rejeição** | {formatar_percentual_br(kpis['taxa_rejeicao_pct'])} | {formatar_numero_br(kpis['registros_rejeitados'], 0)} inconsistências |",
            "",
        ]
    )

    if kpis["registros_validos"] == 0:
        linhas.extend(
            [
                "## 2. Diagnóstico Comercial",
                "",
                "Nenhuma venda válida restou após a camada de validação. Não há faturamento, rankings ou evolução mensal a apresentar. Consulte `inconsistencias.csv` e `relatorio_qualidade.md` para investigar os motivos de rejeição.",
                "",
            ]
        )
        return "\n".join(linhas)

    # Desempenho por Loja
    linhas.extend(
        [
            "## 2. Desempenho por Loja",
            "",
            "| Ranking | Loja | Pedidos | Unidades | Faturamento | Ticket Médio | Participação |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in analises["lojas"].to_dict(orient="records"):
        linhas.append(
            f"| {item['Ranking']} | {_escapar_celula_markdown(item['Loja'])} | "
            f"{formatar_numero_br(item['Pedidos'], 0)} | "
            f"{formatar_numero_br(item['Quantidade'], 0)} | "
            f"{formatar_moeda_br(item['Faturamento'])} | "
            f"{formatar_moeda_br(item['Ticket Médio'])} | "
            f"{formatar_percentual_br(item['Participação (%)'])} |"
        )

    # Desempenho por Categoria
    linhas.extend(
        [
            "",
            "## 3. Desempenho por Categoria",
            "",
            "| Ranking | Categoria | Produtos Distintos | Unidades | Faturamento | Receita/Unid. | Participação |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in analises["categorias"].to_dict(orient="records"):
        linhas.append(
            f"| {item['Ranking']} | {_escapar_celula_markdown(item['Categoria'])} | "
            f"{formatar_numero_br(item['Produtos Distintos'], 0)} | "
            f"{formatar_numero_br(item['Quantidade'], 0)} | "
            f"{formatar_moeda_br(item['Faturamento'])} | "
            f"{formatar_moeda_br(item['Receita por Unidade'])} | "
            f"{formatar_percentual_br(item['Participação (%)'])} |"
        )

    # Ranking de Produtos (até Top 15 para manter legibilidade em bases grandes)
    produtos_lista = analises["produtos"].to_dict(orient="records")
    limite_produtos = min(len(produtos_lista), 15)
    titulo_produtos = (
        "## 4. Ranking de Produtos"
        if len(produtos_lista) <= 15
        else f"## 4. Ranking de Produtos (Top {limite_produtos} de {len(produtos_lista)})"
    )
    linhas.extend(
        [
            "",
            titulo_produtos,
            "",
            "| Ranking | Produto | Categoria | Unidades | Faturamento | Receita/Unid. | Participação |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in produtos_lista[:limite_produtos]:
        linhas.append(
            f"| {item['Ranking']} | {_escapar_celula_markdown(item['Produto'])} | "
            f"{_escapar_celula_markdown(item['Categoria'])} | "
            f"{formatar_numero_br(item['Quantidade'], 0)} | "
            f"{formatar_moeda_br(item['Faturamento'])} | "
            f"{formatar_moeda_br(item['Receita por Unidade'])} | "
            f"{formatar_percentual_br(item['Participação (%)'])} |"
        )

    # Evolução Mensal e Comparação entre Períodos
    linhas.extend(
        [
            "",
            "## 5. Evolução Mensal e Comparação entre Períodos",
            "",
            "| Mês | Pedidos | Unidades | Faturamento | Ticket Médio | Var. Faturamento (R$) | Var. Faturamento (%) | Var. Unidades (%) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    mensal_lista = analises["mensal"].to_dict(orient="records")
    for item in mensal_lista:
        var_abs = (
            formatar_moeda_br(item["Variação Faturamento (R$)"])
            if item["Variação Faturamento (R$)"] is not None
            else "—"
        )
        var_pct = (
            formatar_percentual_br(item["Variação Faturamento (%)"])
            if item["Variação Faturamento (%)"] is not None
            else "—"
        )
        var_unid = (
            formatar_percentual_br(item["Variação Unidades (%)"])
            if item["Variação Unidades (%)"] is not None
            else "—"
        )
        linhas.append(
            f"| `{item['Ano_Mes']}` | "
            f"{formatar_numero_br(item['Pedidos'], 0)} | "
            f"{formatar_numero_br(item['Quantidade'], 0)} | "
            f"{formatar_moeda_br(item['Faturamento'])} | "
            f"{formatar_moeda_br(item['Ticket Médio'])} | "
            f"{var_abs} | {var_pct} | {var_unid} |"
        )

    # Interpretação Empresarial Objetiva baseada somente nos dados processados
    lojas_lista = analises["lojas"].to_dict(orient="records")
    categorias_lista = analises["categorias"].to_dict(orient="records")
    loja_lider = lojas_lista[0]
    loja_menor = lojas_lista[-1]
    cat_lider = categorias_lista[0]
    prod_lider = produtos_lista[0]

    linhas.extend(
        [
            "",
            "## 6. Síntese Empresarial Baseada nos Dados Processados",
            "",
            f"- **Liderança entre lojas:** `{loja_lider['Loja']}` concentrou **{formatar_percentual_br(loja_lider['Participação (%)'])}** do faturamento ({formatar_moeda_br(loja_lider['Faturamento'])} em {formatar_numero_br(loja_lider['Pedidos'], 0)} pedidos), enquanto `{loja_menor['Loja']}` registrou a menor participação ({formatar_percentual_br(loja_menor['Participação (%)'])}, {formatar_moeda_br(loja_menor['Faturamento'])}).",
            f"- **Concentração por categoria e produto:** `{cat_lider['Categoria']}` liderou as categorias com **{formatar_percentual_br(cat_lider['Participação (%)'])}** da receita ({formatar_moeda_br(cat_lider['Faturamento'])}), e `{prod_lider['Produto']}` foi o produto de maior faturamento ({formatar_moeda_br(prod_lider['Faturamento'])}, {formatar_percentual_br(prod_lider['Participação (%)'])} do total).",
        ]
    )

    if len(mensal_lista) >= 2:
        primeiro_mes = mensal_lista[0]
        ultimo_mes = mensal_lista[-1]
        variacao_total = ultimo_mes["Faturamento"] - primeiro_mes["Faturamento"]
        variacao_total_pct = (
            (variacao_total * Decimal("100")) / primeiro_mes["Faturamento"]
            if primeiro_mes["Faturamento"] > Decimal("0")
            else Decimal("0.00")
        )
        linhas.append(
            f"- **Tendência entre períodos:** entre `{primeiro_mes['Ano_Mes']}` ({formatar_moeda_br(primeiro_mes['Faturamento'])}) e `{ultimo_mes['Ano_Mes']}` ({formatar_moeda_br(ultimo_mes['Faturamento'])}), a variação acumulada de faturamento foi de **{formatar_moeda_br(variacao_total)}** ({formatar_percentual_br(variacao_total_pct)})."
        )

    linhas.append(
        f"- **Qualidade dos dados:** foram rejeitados **{formatar_numero_br(resultado_validacao['total_registros_rejeitados'], 0)}** registros ({formatar_percentual_br(resultado_validacao['taxa_rejeicao_pct'])}) e sinalizados **{len(resultado_validacao['alertas_investigacao'])}** alerta(s) de investigação (`Pedido + Produto` recorrente)."
    )
    linhas.append("")

    return "\n".join(linhas)


def gerar_resumo_execucao_dict(
    timestamp_execucao,
    duracao_segundos,
    status_execucao,
    resultado_ingestao,
    resultado_validacao,
    kpis,
    resultado_reconciliacao,
    arquivos_gerados,
):
    """Monta dicionário JSON-serializável com o resumo completo da execução."""
    verificacoes_json = []
    for item in resultado_reconciliacao["verificacoes"]:
        def _serializar(val):
            if isinstance(val, Decimal):
                return "0.00" if val == Decimal("0") else format(val.normalize(), "f")
            return str(val)

        verificacoes_json.append(
            {
                "codigo": item["codigo"],
                "nome": item["nome"],
                "formula": item["formula"],
                "valor_esperado": _serializar(item["valor_esperado"]),
                "valor_obtido": _serializar(item["valor_obtido"]),
                "diferenca": _serializar(item["diferenca"]),
                "aprovada": item["aprovada"],
            }
        )

    return {
        "timestamp_execucao": timestamp_execucao,
        "duracao_segundos": round(duracao_segundos, 4),
        "status_execucao": status_execucao,
        "flags": {
            "todos_arquivos_aceitos": len(resultado_ingestao["arquivos_rejeitados"]) == 0,
            "reconciliacao_aprovada": resultado_reconciliacao["aprovada"],
            "possui_vendas_validas": kpis["registros_validos"] > 0,
            "possui_alertas_investigacao": len(resultado_validacao["alertas_investigacao"]) > 0,
        },
        "ingestao": {
            "pasta_entrada": resultado_ingestao["pasta_entrada"],
            "total_arquivos_encontrados": resultado_ingestao["total_arquivos_encontrados"],
            "arquivos_aceitos": resultado_ingestao["arquivos_aceitos"],
            "arquivos_rejeitados": resultado_ingestao["arquivos_rejeitados"],
            "total_registros_recebidos": resultado_ingestao["total_registros_recebidos"],
        },
        "qualidade": {
            "registros_validos": resultado_validacao["total_registros_validos"],
            "registros_rejeitados": resultado_validacao["total_registros_rejeitados"],
            "linhas_multiplos_erros": resultado_validacao["total_linhas_multiplos_erros"],
            "taxa_rejeicao_pct": str(
                resultado_validacao["taxa_rejeicao_pct"].quantize(
                    CASAS_DECIMAIS_PERCENTUAL, rounding=ROUND_HALF_UP
                )
            ),
            "contagem_motivos": resultado_validacao["contagem_motivos"],
            "pedidos_conflito_data": resultado_validacao["pedidos_conflito_data"],
            "pedidos_conflito_loja": resultado_validacao["pedidos_conflito_loja"],
            "total_alertas_investigacao": len(resultado_validacao["alertas_investigacao"]),
            "alertas_investigacao": resultado_validacao["alertas_investigacao"],
        },
        "kpis": {
            "faturamento_total": str(kpis["faturamento_total"]),
            "quantidade_pedidos": kpis["quantidade_pedidos"],
            "unidades_vendidas": kpis["unidades_vendidas"],
            "ticket_medio_pedido": str(
                kpis["ticket_medio_pedido"].quantize(
                    CASAS_DECIMAIS_MOEDA, rounding=ROUND_HALF_UP
                )
            ),
            "receita_por_unidade": str(
                kpis["receita_por_unidade"].quantize(
                    CASAS_DECIMAIS_MOEDA, rounding=ROUND_HALF_UP
                )
            ),
        },
        "reconciliacao": {
            "aprovada": resultado_reconciliacao["aprovada"],
            "total_verificacoes": resultado_reconciliacao["total_verificacoes"],
            "total_aprovadas": resultado_reconciliacao["total_aprovadas"],
            "total_reprovadas": resultado_reconciliacao["total_reprovadas"],
            "linhas_com_ruido_float": resultado_reconciliacao["comparacao_float_vs_decimal"]["linhas_com_ruido_float"],
            "diferenca_float_vs_decimal": (
                "0.00"
                if resultado_reconciliacao["comparacao_float_vs_decimal"]["diferenca_float_vs_decimal"]
                == Decimal("0")
                else format(
                    resultado_reconciliacao["comparacao_float_vs_decimal"]["diferenca_float_vs_decimal"].normalize(),
                    "f",
                )
            ),
            "verificacoes": verificacoes_json,
        },
        "arquivos_gerados": arquivos_gerados,
    }


def exportar_resultados(
    pasta_saida,
    timestamp_execucao,
    duracao_segundos,
    status_execucao,
    resultado_ingestao,
    resultado_validacao,
    vendas_validas,
    inconsistencias,
    kpis,
    tabela_kpis,
    analises,
    resultado_reconciliacao,
):
    """Exporta CSVs, relatórios Markdown e JSON com gravação atômica por arquivo e rollback do lote.

    Cada arquivo individual é substituído via temporário (``.tmp`` -> ``replace()``).
    Antes de iniciar a gravação, os arquivos já existentes na pasta de saída têm seus
    bytes preservados em memória para rollback em melhor esforço caso ocorra falha no
    meio do lote, evitando mistura de relatórios entre execuções distintas.
    """
    destino = Path(pasta_saida)
    destino.mkdir(parents=True, exist_ok=True)

    # Prepara todos os conteúdos em memória antes de gravar no disco
    vendas_csv = _preparar_csv_texto(_preparar_vendas_para_csv(vendas_validas))
    inconsistencias_csv = _preparar_csv_texto(inconsistencias)
    kpis_csv = _preparar_csv_texto(_preparar_kpis_para_csv(tabela_kpis))

    lojas_csv = _preparar_csv_texto(
        _preparar_analise_para_csv(
            analises["lojas"],
            colunas_exatas=["Faturamento"],
            colunas_arredondadas=["Ticket Médio", "Receita por Unidade", "Participação (%)"],
        )
    )
    produtos_csv = _preparar_csv_texto(
        _preparar_analise_para_csv(
            analises["produtos"],
            colunas_exatas=["Faturamento"],
            colunas_arredondadas=["Receita por Unidade", "Participação (%)"],
        )
    )
    categorias_csv = _preparar_csv_texto(
        _preparar_analise_para_csv(
            analises["categorias"],
            colunas_exatas=["Faturamento"],
            colunas_arredondadas=["Receita por Unidade", "Participação (%)"],
        )
    )
    mensal_csv = _preparar_csv_texto(
        _preparar_analise_para_csv(
            analises["mensal"],
            colunas_exatas=[
                "Faturamento",
                "Faturamento Período Anterior",
                "Variação Faturamento (R$)",
            ],
            colunas_arredondadas=[
                "Ticket Médio",
                "Receita por Unidade",
                "Participação (%)",
                "Variação Faturamento (%)",
                "Variação Unidades (%)",
            ],
        )
    )

    relatorio_qualidade = gerar_relatorio_qualidade_md(
        timestamp_execucao=timestamp_execucao,
        status_execucao=status_execucao,
        resultado_ingestao=resultado_ingestao,
        resultado_validacao=resultado_validacao,
    )
    relatorio_reconciliacao = gerar_relatorio_reconciliacao_md(
        timestamp_execucao=timestamp_execucao,
        status_execucao=status_execucao,
        resultado_reconciliacao=resultado_reconciliacao,
    )
    relatorio_executivo = gerar_relatorio_executivo_md(
        timestamp_execucao=timestamp_execucao,
        status_execucao=status_execucao,
        resultado_ingestao=resultado_ingestao,
        resultado_validacao=resultado_validacao,
        kpis=kpis,
        analises=analises,
        resultado_reconciliacao=resultado_reconciliacao,
    )

    nomes_gerados = list(ARQUIVOS_SAIDA.values())
    resumo_dict = gerar_resumo_execucao_dict(
        timestamp_execucao=timestamp_execucao,
        duracao_segundos=duracao_segundos,
        status_execucao=status_execucao,
        resultado_ingestao=resultado_ingestao,
        resultado_validacao=resultado_validacao,
        kpis=kpis,
        resultado_reconciliacao=resultado_reconciliacao,
        arquivos_gerados=nomes_gerados,
    )
    resumo_json = json.dumps(resumo_dict, ensure_ascii=False, indent=2) + "\n"

    conteudos = {
        ARQUIVOS_SAIDA["vendas_tratadas"]: vendas_csv,
        ARQUIVOS_SAIDA["inconsistencias"]: inconsistencias_csv,
        ARQUIVOS_SAIDA["kpis_executivos"]: kpis_csv,
        ARQUIVOS_SAIDA["analise_lojas"]: lojas_csv,
        ARQUIVOS_SAIDA["analise_produtos"]: produtos_csv,
        ARQUIVOS_SAIDA["analise_categorias"]: categorias_csv,
        ARQUIVOS_SAIDA["analise_mensal"]: mensal_csv,
        ARQUIVOS_SAIDA["relatorio_qualidade"]: relatorio_qualidade,
        ARQUIVOS_SAIDA["relatorio_reconciliacao"]: relatorio_reconciliacao,
        ARQUIVOS_SAIDA["relatorio_executivo"]: relatorio_executivo,
        ARQUIVOS_SAIDA["resumo_execucao"]: resumo_json,
    }

    # Captura snapshot dos arquivos existentes antes de alterar o lote na pasta de saída
    backups_anteriores = {}
    for nome_arquivo in conteudos:
        caminho_destino = destino / nome_arquivo
        if caminho_destino.exists():
            backups_anteriores[caminho_destino] = caminho_destino.read_bytes()
        else:
            backups_anteriores[caminho_destino] = None

    caminhos_salvos = []
    try:
        for nome_arquivo, texto in conteudos.items():
            caminho_destino = destino / nome_arquivo
            _escrever_texto_atomico(caminho_destino, texto)
            caminhos_salvos.append(caminho_destino)
    except Exception as erro:
        # Rollback em melhor esforço para evitar mistura de arquivos entre execuções
        erros_rollback = []
        for caminho_alterado in caminhos_salvos:
            conteudo_anterior = backups_anteriores.get(caminho_alterado)
            try:
                if conteudo_anterior is None:
                    if caminho_alterado.exists():
                        caminho_alterado.unlink()
                else:
                    caminho_restore = caminho_alterado.with_name(
                        caminho_alterado.name + ".restore.tmp"
                    )
                    caminho_restore.write_bytes(conteudo_anterior)
                    caminho_restore.replace(caminho_alterado)
            except OSError as erro_restore:
                erros_rollback.append(f"{caminho_alterado.name}: {erro_restore}")

        for nome_arquivo in conteudos:
            caminho_tmp = destino / (nome_arquivo + ".tmp")
            if caminho_tmp.exists():
                try:
                    caminho_tmp.unlink()
                except OSError:
                    pass

        if len(erros_rollback) > 0:
            detalhes_rb = "; ".join(erros_rollback)
            raise RuntimeError(
                "Falha durante a exportação do lote e rollback parcial incompleto "
                f"({detalhes_rb}). Erro original: {erro}"
            ) from erro

        raise RuntimeError(
            "Falha durante a exportação do lote de relatórios; os arquivos anteriores "
            f"foram restaurados por rollback para preservar a consistência. Detalhe: {erro}"
        ) from erro

    # Remove artefato gráfico legado da V1 somente após todos os 11 arquivos concluírem
    grafico_legado = destino / "resumo_vendas.png"
    if grafico_legado.exists():
        grafico_legado.unlink()

    return caminhos_salvos, resumo_dict
