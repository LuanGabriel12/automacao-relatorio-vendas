"""Leitura, tratamento e criação do relatório de vendas."""

import logging
from pathlib import Path

import pandas as pd
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


COLUNAS = [
    "data",
    "pedido",
    "loja",
    "produto",
    "categoria",
    "quantidade",
    "preco_unitario",
]

NOMES_COLUNAS = {
    "Data": "data",
    "Pedido": "pedido",
    "Loja": "loja",
    "Produto": "produto",
    "Categoria": "categoria",
    "Quantidade": "quantidade",
    "Preço Unitário": "preco_unitario",
}

NOMES_EXCEL = {
    "data": "Data",
    "pedido": "Pedido",
    "loja": "Loja",
    "produto": "Produto",
    "categoria": "Categoria",
    "quantidade": "Quantidade",
    "preco_unitario": "Preço Unitário",
    "faturamento": "Faturamento",
    "mes": "Mês",
    "pedidos": "Pedidos",
    "ticket_medio": "Ticket Médio",
    "arquivo_origem": "Arquivo de Origem",
    "motivo_descarte": "Motivo do Descarte",
}

AZUL_ESCURO = "17324D"
AZUL = "2F75B5"
VERDE = "2A9D8F"
BRANCO = "FFFFFF"
CINZA = "52606D"
CINZA_CLARO = "E8EDF2"
FUNDO = "F6F8FA"


def configurar_log(caminho_log):
    caminho_log.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=caminho_log,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        encoding="utf-8",
        force=True,
    )


def ler_csv(caminho):
    """Lê CSV separado por ponto e vírgula, aceitando UTF-8 e Latin-1."""

    try:
        return pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(caminho, sep=";", dtype=str, encoding="latin-1")


def carregar_vendas(pasta_entrada):
    """Lê os arquivos da pasta e junta tudo em um DataFrame."""

    arquivos_csv = list(pasta_entrada.glob("*.csv"))
    arquivos_excel = list(pasta_entrada.glob("*.xlsx"))
    arquivos = sorted(arquivos_csv + arquivos_excel)

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo CSV ou XLSX foi encontrado em {pasta_entrada}."
        )

    tabelas = []

    for arquivo in arquivos:
        if arquivo.name.startswith("~$"):
            continue

        if arquivo.suffix.lower() == ".csv":
            dados = ler_csv(arquivo)
        else:
            dados = pd.read_excel(arquivo, dtype=str)

        dados.columns = [str(coluna).strip() for coluna in dados.columns]
        dados = dados.rename(columns=NOMES_COLUNAS)

        colunas_ausentes = [coluna for coluna in COLUNAS if coluna not in dados]
        if colunas_ausentes:
            ausentes = ", ".join(colunas_ausentes)
            raise ValueError(f"{arquivo.name}: colunas ausentes: {ausentes}.")

        dados = dados[COLUNAS].copy()
        dados["arquivo_origem"] = arquivo.name
        tabelas.append(dados)
        logging.info("Arquivo lido: %s", arquivo.name)

    if not tabelas:
        raise FileNotFoundError("Não foi possível ler nenhum arquivo de entrada.")

    return pd.concat(tabelas, ignore_index=True)


def converter_numero_brasileiro(valor):
    """Converte textos como 1.299,90 para 1299.90."""

    if pd.isna(valor):
        return float("nan")

    texto = str(valor).replace("R$", "").replace(" ", "").strip()
    if not texto:
        return float("nan")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return float("nan")


def encontrar_problemas(linha):
    """Retorna os problemas encontrados em uma linha."""

    problemas = []

    if pd.isna(linha["data"]):
        problemas.append("Data inválida ou ausente")

    for coluna, nome in [
        ("pedido", "Pedido"),
        ("loja", "Loja"),
        ("produto", "Produto"),
        ("categoria", "Categoria"),
    ]:
        if pd.isna(linha[coluna]):
            problemas.append(f"{nome} ausente")

    if pd.isna(linha["quantidade"]) or linha["quantidade"] <= 0:
        problemas.append("Quantidade inválida")

    if pd.isna(linha["preco_unitario"]) or linha["preco_unitario"] <= 0:
        problemas.append("Preço unitário inválido")

    return "; ".join(problemas)


def limpar_vendas(dados_brutos):
    """Limpa os dados e separa as linhas que não podem entrar na análise."""

    dados = dados_brutos.copy()

    for coluna in ["pedido", "loja", "produto", "categoria"]:
        dados[coluna] = dados[coluna].astype("string").str.strip()
        dados[coluna] = dados[coluna].replace("", pd.NA)

    dados["data"] = pd.to_datetime(
        dados["data"],
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )
    dados["quantidade"] = dados["quantidade"].map(converter_numero_brasileiro)
    dados["preco_unitario"] = dados["preco_unitario"].map(
        converter_numero_brasileiro
    )

    duplicada = dados.duplicated(subset=COLUNAS, keep="first")
    duplicados = dados.loc[duplicada].copy()
    duplicados["motivo_descarte"] = "Registro duplicado"

    dados = dados.loc[~duplicada].copy()
    dados["motivo_descarte"] = dados.apply(encontrar_problemas, axis=1)

    invalida = dados["motivo_descarte"].ne("")
    inconsistencias = dados.loc[invalida].copy()
    inconsistencias = pd.concat(
        [inconsistencias, duplicados],
        ignore_index=True,
        sort=False,
    )

    vendas = dados.loc[~invalida].copy()
    vendas["quantidade"] = vendas["quantidade"].astype(int)
    vendas["faturamento"] = (
        vendas["quantidade"] * vendas["preco_unitario"]
    ).round(2)
    vendas["mes"] = vendas["data"].dt.strftime("%Y-%m")
    vendas = vendas.sort_values(["data", "pedido"]).reset_index(drop=True)

    return vendas, inconsistencias, int(duplicada.sum())


def criar_analises(vendas):
    """Cria os resumos usados nas abas do relatório."""

    por_loja = (
        vendas.groupby("loja", as_index=False)
        .agg(
            faturamento=("faturamento", "sum"),
            quantidade=("quantidade", "sum"),
            pedidos=("pedido", "nunique"),
        )
        .sort_values("faturamento", ascending=False)
        .reset_index(drop=True)
    )
    por_loja["ticket_medio"] = (
        por_loja["faturamento"] / por_loja["pedidos"]
    ).round(2)

    por_produto = (
        vendas.groupby(["produto", "categoria"], as_index=False)
        .agg(
            faturamento=("faturamento", "sum"),
            quantidade=("quantidade", "sum"),
            pedidos=("pedido", "nunique"),
        )
        .sort_values("faturamento", ascending=False)
        .reset_index(drop=True)
    )

    por_categoria = (
        vendas.groupby("categoria", as_index=False)
        .agg(
            faturamento=("faturamento", "sum"),
            quantidade=("quantidade", "sum"),
        )
        .sort_values("faturamento", ascending=False)
        .reset_index(drop=True)
    )

    por_mes = (
        vendas.groupby("mes", as_index=False)
        .agg(
            faturamento=("faturamento", "sum"),
            quantidade=("quantidade", "sum"),
            pedidos=("pedido", "nunique"),
        )
        .sort_values("mes")
        .reset_index(drop=True)
    )
    por_mes["ticket_medio"] = (
        por_mes["faturamento"] / por_mes["pedidos"]
    ).round(2)

    return {
        "por_loja": por_loja,
        "por_produto": por_produto,
        "por_categoria": por_categoria,
        "por_mes": por_mes,
    }


def calcular_kpis(vendas, inconsistencias):
    faturamento = float(vendas["faturamento"].sum())
    pedidos = int(vendas["pedido"].nunique())

    return {
        "faturamento_total": round(faturamento, 2),
        "quantidade_total": int(vendas["quantidade"].sum()),
        "pedidos_unicos": pedidos,
        "ticket_medio": round(faturamento / pedidos, 2) if pedidos else 0,
        "registros_validos": len(vendas),
        "registros_descartados": len(inconsistencias),
    }


def adicionar_tabela(ws, nome):
    if ws.max_row < 5:
        return

    ultima_coluna = get_column_letter(ws.max_column)
    tabela = Table(
        displayName=nome,
        ref=f"A4:{ultima_coluna}{ws.max_row}",
    )
    tabela.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(tabela)


def formatar_aba(ws, titulo, subtitulo, nome_tabela):
    """Aplica a formatação comum das abas de dados."""

    ultima_linha = ws.max_row
    ultima_coluna = ws.max_column
    letra_final = get_column_letter(ultima_coluna)

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"
    ws.merge_cells(f"A1:{letra_final}1")
    ws.merge_cells(f"A2:{letra_final}2")

    ws["A1"] = titulo
    ws["A1"].fill = PatternFill("solid", fgColor=AZUL_ESCURO)
    ws["A1"].font = Font(color=BRANCO, bold=True, size=16)
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30

    ws["A2"] = subtitulo
    ws["A2"].font = Font(color=CINZA, italic=True, size=10)
    ws.row_dimensions[2].height = 20

    for celula in ws[4]:
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.font = Font(color=BRANCO, bold=True)
        celula.alignment = Alignment(horizontal="center")

    adicionar_tabela(ws, nome_tabela)

    cabecalhos = {
        ws.cell(4, coluna).value: coluna
        for coluna in range(1, ultima_coluna + 1)
    }

    if ultima_linha >= 5:
        for cabecalho in ["Preço Unitário", "Faturamento", "Ticket Médio"]:
            if cabecalho in cabecalhos:
                coluna = cabecalhos[cabecalho]
                for linha in range(5, ultima_linha + 1):
                    ws.cell(linha, coluna).number_format = '"R$" #,##0.00'

        if "Data" in cabecalhos:
            coluna = cabecalhos["Data"]
            for linha in range(5, ultima_linha + 1):
                ws.cell(linha, coluna).number_format = "dd/mm/yyyy"

        if "Faturamento" in cabecalhos:
            letra = get_column_letter(cabecalhos["Faturamento"])
            ws.conditional_formatting.add(
                f"{letra}5:{letra}{ultima_linha}",
                ColorScaleRule(
                    start_type="min",
                    start_color="FDE8E7",
                    end_type="max",
                    end_color="DDF1EA",
                ),
            )

    for coluna in range(1, ultima_coluna + 1):
        valores = [
            str(ws.cell(linha, coluna).value or "")
            for linha in range(4, ultima_linha + 1)
        ]
        largura = max((len(valor) for valor in valores), default=10) + 2
        ws.column_dimensions[get_column_letter(coluna)].width = min(
            max(largura, 12),
            32,
        )


def estilizar_bloco(ws, intervalo, cor):
    borda = Side(style="thin", color=CINZA_CLARO)

    for linha in ws[intervalo]:
        for celula in linha:
            celula.fill = PatternFill("solid", fgColor=cor)
            celula.border = Border(
                left=borda,
                right=borda,
                top=borda,
                bottom=borda,
            )


def montar_resumo(wb, analises, kpis):
    """Cria a primeira aba com os principais números e gráficos."""

    ws = wb.create_sheet("Resumo", 0)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"
    ws.sheet_properties.tabColor = AZUL_ESCURO

    ws.merge_cells("A1:L1")
    ws["A1"] = "RELATÓRIO DE VENDAS"
    ws["A1"].fill = PatternFill("solid", fgColor=AZUL_ESCURO)
    ws["A1"].font = Font(color=BRANCO, bold=True, size=18)
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 34

    ws.merge_cells("A2:L2")
    ws["A2"] = (
        f"{kpis['registros_validos']} registros válidos e "
        f"{kpis['registros_descartados']} descartados"
    )
    ws["A2"].font = Font(color=CINZA, italic=True)

    cards = [
        (1, 3, "FATURAMENTO", kpis["faturamento_total"], '"R$" #,##0.00', AZUL),
        (4, 6, "ITENS VENDIDOS", kpis["quantidade_total"], "#,##0", VERDE),
        (7, 9, "PEDIDOS", kpis["pedidos_unicos"], "#,##0", "6C7A89"),
        (10, 12, "TICKET MÉDIO", kpis["ticket_medio"], '"R$" #,##0.00', "D9903D"),
    ]

    for inicio, fim, titulo, valor, formato, cor in cards:
        letra_inicio = get_column_letter(inicio)
        letra_fim = get_column_letter(fim)

        ws.merge_cells(f"{letra_inicio}4:{letra_fim}4")
        ws.merge_cells(f"{letra_inicio}5:{letra_fim}7")
        estilizar_bloco(ws, f"{letra_inicio}4:{letra_fim}4", cor)
        estilizar_bloco(ws, f"{letra_inicio}5:{letra_fim}7", FUNDO)

        ws.cell(4, inicio, titulo)
        ws.cell(4, inicio).font = Font(color=BRANCO, bold=True)
        ws.cell(4, inicio).alignment = Alignment(horizontal="center")

        ws.cell(5, inicio, valor)
        ws.cell(5, inicio).font = Font(color=AZUL_ESCURO, bold=True, size=20)
        ws.cell(5, inicio).number_format = formato
        ws.cell(5, inicio).alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    ws.merge_cells("A10:E10")
    ws["A10"] = "RESULTADO POR LOJA"
    ws["A10"].font = Font(color=AZUL_ESCURO, bold=True, size=12)

    cabecalhos = ["Loja", "Faturamento", "Quantidade", "Pedidos", "Ticket Médio"]
    for coluna, cabecalho in enumerate(cabecalhos, start=1):
        ws.cell(11, coluna, cabecalho)

    por_loja = analises["por_loja"]
    for linha, registro in enumerate(por_loja.itertuples(index=False), start=12):
        ws.cell(linha, 1, registro.loja)
        ws.cell(linha, 2, registro.faturamento)
        ws.cell(linha, 3, registro.quantidade)
        ws.cell(linha, 4, registro.pedidos)
        ws.cell(linha, 5, registro.ticket_medio)

    ultima_loja = 11 + len(por_loja)
    for celula in ws[11][:5]:
        celula.fill = PatternFill("solid", fgColor=AZUL_ESCURO)
        celula.font = Font(color=BRANCO, bold=True)
        celula.alignment = Alignment(horizontal="center")

    for linha in range(12, ultima_loja + 1):
        ws.cell(linha, 2).number_format = '"R$" #,##0.00'
        ws.cell(linha, 5).number_format = '"R$" #,##0.00'

    ws.merge_cells("A20:D20")
    ws["A20"] = "PRODUTOS COM MAIOR FATURAMENTO"
    ws["A20"].font = Font(color=AZUL_ESCURO, bold=True, size=12)

    cabecalhos_produto = ["Produto", "Categoria", "Faturamento", "Quantidade"]
    for coluna, cabecalho in enumerate(cabecalhos_produto, start=1):
        ws.cell(21, coluna, cabecalho)
        ws.cell(21, coluna).fill = PatternFill("solid", fgColor=AZUL_ESCURO)
        ws.cell(21, coluna).font = Font(color=BRANCO, bold=True)
        ws.cell(21, coluna).alignment = Alignment(horizontal="center")

    top_produtos = analises["por_produto"].head(5)
    for linha, registro in enumerate(top_produtos.itertuples(index=False), start=22):
        ws.cell(linha, 1, registro.produto)
        ws.cell(linha, 2, registro.categoria)
        ws.cell(linha, 3, registro.faturamento)
        ws.cell(linha, 4, registro.quantidade)
        ws.cell(linha, 3).number_format = '"R$" #,##0.00'

    planilha_lojas = wb["Por_Loja"]
    grafico_lojas = BarChart()
    grafico_lojas.type = "bar"
    grafico_lojas.style = 10
    grafico_lojas.title = "Faturamento por loja"
    grafico_lojas.height = 7.4
    grafico_lojas.width = 13.2
    grafico_lojas.legend = None
    grafico_lojas.x_axis.numFmt = '"R$" #,##0'
    dados_lojas = Reference(
        planilha_lojas,
        min_col=2,
        min_row=4,
        max_row=4 + len(por_loja),
    )
    categorias_lojas = Reference(
        planilha_lojas,
        min_col=1,
        min_row=5,
        max_row=4 + len(por_loja),
    )
    grafico_lojas.add_data(dados_lojas, titles_from_data=True)
    grafico_lojas.set_categories(categorias_lojas)
    grafico_lojas.series[0].graphicalProperties.solidFill = AZUL
    grafico_lojas.dLbls = DataLabelList()
    grafico_lojas.dLbls.showVal = True
    ws.add_chart(grafico_lojas, "G10")

    por_mes = analises["por_mes"]
    planilha_meses = wb["Por_Mes"]
    grafico_meses = LineChart()
    grafico_meses.style = 13
    grafico_meses.title = "Faturamento por mês"
    grafico_meses.height = 7.4
    grafico_meses.width = 13.2
    grafico_meses.legend = None
    grafico_meses.y_axis.numFmt = '"R$" #,##0'
    dados_meses = Reference(
        planilha_meses,
        min_col=2,
        min_row=4,
        max_row=4 + len(por_mes),
    )
    categorias_meses = Reference(
        planilha_meses,
        min_col=1,
        min_row=5,
        max_row=4 + len(por_mes),
    )
    grafico_meses.add_data(dados_meses, titles_from_data=True)
    grafico_meses.set_categories(categorias_meses)
    grafico_meses.series[0].graphicalProperties.line.solidFill = VERDE
    grafico_meses.series[0].marker.symbol = "circle"
    ws.add_chart(grafico_meses, "G25")

    larguras = {
        "A": 27,
        "B": 18,
        "C": 16,
        "D": 16,
        "E": 18,
        "F": 3,
        "G": 14,
        "H": 14,
        "I": 14,
        "J": 14,
        "K": 14,
        "L": 14,
    }
    for coluna, largura in larguras.items():
        ws.column_dimensions[coluna].width = largura


def gerar_relatorio_excel(vendas, inconsistencias, analises, kpis, caminho_saida):
    """Gera o arquivo Excel com os dados e os resumos."""

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    vendas_excel = vendas[
        [
            "data",
            "pedido",
            "loja",
            "produto",
            "categoria",
            "quantidade",
            "preco_unitario",
            "faturamento",
            "mes",
            "arquivo_origem",
        ]
    ].rename(columns=NOMES_EXCEL)

    colunas_erros = [
        "data",
        "pedido",
        "loja",
        "produto",
        "categoria",
        "quantidade",
        "preco_unitario",
        "arquivo_origem",
        "motivo_descarte",
    ]
    erros_excel = inconsistencias.reindex(columns=colunas_erros).rename(
        columns=NOMES_EXCEL
    )

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        abas = {
            "Vendas_Limpas": vendas_excel,
            "Por_Loja": analises["por_loja"].rename(columns=NOMES_EXCEL),
            "Por_Produto": analises["por_produto"].rename(columns=NOMES_EXCEL),
            "Por_Categoria": analises["por_categoria"].rename(columns=NOMES_EXCEL),
            "Por_Mes": analises["por_mes"].rename(columns=NOMES_EXCEL),
            "Inconsistencias": erros_excel,
        }

        for nome_aba, dados in abas.items():
            dados.to_excel(writer, sheet_name=nome_aba, index=False, startrow=3)

        wb = writer.book
        wb.properties.title = "Relatório de Vendas"
        wb.properties.subject = "Consolidação e análise de vendas"
        wb.calculation.calcMode = "auto"

        configuracoes = {
            "Vendas_Limpas": (
                "VENDAS TRATADAS",
                "Base consolidada usada nos cálculos.",
                "TabelaVendas",
                AZUL,
            ),
            "Por_Loja": (
                "ANÁLISE POR LOJA",
                "Faturamento, quantidade, pedidos e ticket médio.",
                "TabelaLojas",
                VERDE,
            ),
            "Por_Produto": (
                "ANÁLISE POR PRODUTO",
                "Produtos ordenados por faturamento.",
                "TabelaProdutos",
                "6C7A89",
            ),
            "Por_Categoria": (
                "ANÁLISE POR CATEGORIA",
                "Resultado consolidado por categoria.",
                "TabelaCategorias",
                "8E6BBE",
            ),
            "Por_Mes": (
                "ANÁLISE MENSAL",
                "Evolução dos indicadores ao longo dos meses.",
                "TabelaMeses",
                "D9903D",
            ),
            "Inconsistencias": (
                "INCONSISTÊNCIAS",
                "Registros que não foram usados nos cálculos.",
                "TabelaInconsistencias",
                "C65353",
            ),
        }

        for nome_aba, (titulo, subtitulo, tabela, cor) in configuracoes.items():
            ws = wb[nome_aba]
            ws.sheet_properties.tabColor = cor
            formatar_aba(ws, titulo, subtitulo, tabela)

        montar_resumo(wb, analises, kpis)
        wb.active = 0


def executar_pipeline(pasta_entrada, caminho_saida, caminho_log):
    """Executa todas as etapas da automação."""

    configurar_log(caminho_log)
    logging.info("Início da execução")

    try:
        dados_brutos = carregar_vendas(pasta_entrada)
        vendas, inconsistencias, duplicados = limpar_vendas(dados_brutos)

        if vendas.empty:
            raise ValueError("Nenhuma venda válida foi encontrada.")

        analises = criar_analises(vendas)
        kpis = calcular_kpis(vendas, inconsistencias)
        gerar_relatorio_excel(
            vendas,
            inconsistencias,
            analises,
            kpis,
            caminho_saida,
        )

        logging.info("Relatório salvo em %s", caminho_saida)
        return {
            **kpis,
            "duplicados_removidos": duplicados,
            "arquivo_saida": str(caminho_saida),
        }
    finally:
        logging.shutdown()
