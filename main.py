import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


# Arquivos que serão usados na análise
arquivos = [
    "dados/entrada/vendas_janeiro.csv",
    "dados/entrada/vendas_fevereiro.csv",
    "dados/entrada/vendas_marco.csv",
]

# Leitura dos três arquivos
tabelas = []

for arquivo in arquivos:
    dados_mes = pd.read_csv(
        arquivo,
        sep=";",
        decimal=",",
        thousands=".",
    )
    dados_mes["Arquivo de origem"] = arquivo.split("/")[-1]
    tabelas.append(dados_mes)

# Junta os meses em uma única tabela
vendas = pd.concat(tabelas, ignore_index=True)
vendas["Data informada"] = vendas["Data"]

# Converte as datas. Uma data impossível vira um valor vazio.
vendas["Data"] = pd.to_datetime(
    vendas["Data"],
    format="%d/%m/%Y",
    errors="coerce",
)

# Identifica os problemas encontrados em cada linha
vendas["Motivo"] = ""

vendas.loc[vendas["Data"].isna(), "Motivo"] = "Data inválida"

vendas.loc[
    (vendas["Motivo"] == "") & (vendas["Pedido"].fillna("").str.strip() == ""),
    "Motivo",
] = "Pedido ausente"

vendas.loc[
    (vendas["Motivo"] == "") & (vendas["Loja"].fillna("").str.strip() == ""),
    "Motivo",
] = "Loja ausente"

vendas.loc[
    (vendas["Motivo"] == "") & (vendas["Produto"].fillna("").str.strip() == ""),
    "Motivo",
] = "Produto ausente"

vendas.loc[
    (vendas["Motivo"] == "") & (vendas["Categoria"].fillna("").str.strip() == ""),
    "Motivo",
] = "Categoria ausente"

vendas.loc[
    (vendas["Motivo"] == "")
    & (vendas["Quantidade"].isna() | (vendas["Quantidade"] <= 0)),
    "Motivo",
] = "Quantidade inválida"

vendas.loc[
    (vendas["Motivo"] == "")
    & (vendas["Preço Unitário"].isna() | (vendas["Preço Unitário"] <= 0)),
    "Motivo",
] = "Preço inválido"

colunas_da_venda = [
    "Data",
    "Pedido",
    "Loja",
    "Produto",
    "Categoria",
    "Quantidade",
    "Preço Unitário",
]

linhas_duplicadas = vendas.duplicated(
    subset=colunas_da_venda,
    keep="first",
)

vendas.loc[
    (vendas["Motivo"] == "") & linhas_duplicadas,
    "Motivo",
] = "Registro duplicado"

# O NumPy cria o status de acordo com o resultado da validação
vendas["Status"] = np.where(
    vendas["Motivo"] == "",
    "Válido",
    "Inválido",
)

# Separa as vendas corretas das linhas que precisam ser revisadas
vendas_validas = vendas.loc[vendas["Status"] == "Válido"].copy()
inconsistencias = vendas.loc[vendas["Status"] == "Inválido"].copy()

# Calcula o faturamento de cada venda e identifica o mês
vendas_validas["Faturamento"] = (
    vendas_validas["Quantidade"] * vendas_validas["Preço Unitário"]
)
vendas_validas["Mês"] = vendas_validas["Data"].dt.to_period("M").astype(str)

# Indicadores gerais
faturamento_total = vendas_validas["Faturamento"].sum()
itens_vendidos = vendas_validas["Quantidade"].sum()
quantidade_pedidos = vendas_validas["Pedido"].nunique()
ticket_medio = faturamento_total / quantidade_pedidos

# Análise por loja
analise_lojas = (
    vendas_validas.groupby("Loja")[["Quantidade", "Faturamento"]]
    .sum()
    .sort_values("Faturamento", ascending=False)
    .reset_index()
)

# Análise por produto
analise_produtos = (
    vendas_validas.groupby(["Produto", "Categoria"])[["Quantidade", "Faturamento"]]
    .sum()
    .sort_values("Faturamento", ascending=False)
    .reset_index()
)

# Análise por mês
analise_mensal = (
    vendas_validas.groupby("Mês")[["Quantidade", "Faturamento"]]
    .sum()
    .sort_values("Mês")
    .reset_index()
)

# Volta a mostrar as datas no formato usado no Brasil
vendas_validas["Data"] = vendas_validas["Data"].dt.strftime("%d/%m/%Y")
inconsistencias["Data"] = inconsistencias["Data"].dt.strftime("%d/%m/%Y")

# Salva as tabelas em CSV
vendas_validas.to_csv(
    "resultado/vendas_tratadas.csv",
    sep=";",
    decimal=",",
    index=False,
)
inconsistencias.to_csv(
    "resultado/inconsistencias.csv",
    sep=";",
    decimal=",",
    index=False,
)
analise_lojas.to_csv(
    "resultado/analise_lojas.csv",
    sep=";",
    decimal=",",
    index=False,
)
analise_produtos.to_csv(
    "resultado/analise_produtos.csv",
    sep=";",
    decimal=",",
    index=False,
)
analise_mensal.to_csv(
    "resultado/analise_mensal.csv",
    sep=";",
    decimal=",",
    index=False,
)

# Cria um resumo visual com dois gráficos
figura, graficos = plt.subplots(1, 2, figsize=(13, 5))

graficos[0].bar(
    analise_lojas["Loja"],
    analise_lojas["Faturamento"],
    color="#2563eb",
)
graficos[0].set_title("Faturamento por loja")
graficos[0].set_xlabel("Loja")
graficos[0].set_ylabel("Faturamento (R$)")
graficos[0].grid(axis="y", alpha=0.25)

graficos[1].plot(
    analise_mensal["Mês"],
    analise_mensal["Faturamento"],
    marker="o",
    color="#16a34a",
    linewidth=2,
)
graficos[1].set_title("Faturamento por mês")
graficos[1].set_xlabel("Mês")
graficos[1].set_ylabel("Faturamento (R$)")
graficos[1].grid(alpha=0.25)

data_execucao = datetime.now().strftime("%d/%m/%Y às %H:%M")
figura.suptitle("Resumo das vendas - " + data_execucao)
plt.tight_layout()
plt.savefig(
    "resultado/resumo_vendas.png",
    dpi=150,
    bbox_inches="tight",
)
plt.close()

# Mostra no terminal o resultado principal
print("Análise concluída!")
print(f"Vendas válidas: {len(vendas_validas)}")
print(f"Inconsistências: {len(inconsistencias)}")
print(f"Pedidos: {quantidade_pedidos}")
print(f"Itens vendidos: {itens_vendidos}")
print(f"Faturamento total: R$ {faturamento_total:.2f}")
print(f"Ticket médio: R$ {ticket_medio:.2f}")
print("Arquivos salvos na pasta resultado.")
