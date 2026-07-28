# Como o projeto funciona

Este documento resume as decisões principais do projeto e a ordem em que os
dados são processados.

## 1. Leitura dos arquivos

A função `carregar_vendas()` procura arquivos CSV e XLSX dentro de
`dados/entrada`.

Cada arquivo é lido como um DataFrame. Depois, todos são reunidos com:

```python
pd.concat(tabelas, ignore_index=True)
```

O `ignore_index=True` cria um índice novo para a base consolidada.

Também guardo o nome do arquivo de origem em uma coluna. Isso ajuda a localizar
de onde veio uma linha com problema.

## 2. Conversão dos dados

Preços como `1.299,90` chegam como texto. Antes de calcular o faturamento, o
programa remove o ponto de milhar e troca a vírgula decimal por ponto:

```text
1.299,90 -> 1299.90
```

As datas são convertidas com `pd.to_datetime()`. Usei `errors="coerce"` para
transformar datas inválidas em valores ausentes, que depois podem ser
identificados na validação.

## 3. Validação

Uma venda só entra na análise quando possui:

- Data válida;
- Número do pedido;
- Loja, produto e categoria;
- Quantidade maior que zero;
- Preço maior que zero.

As linhas que não passam por essas regras são enviadas para a aba
`Inconsistencias`. Preferi manter esses registros no relatório em vez de
simplesmente apagá-los.

Os registros repetidos também são removidos e identificados como duplicados.

## 4. Cálculos e agrupamentos

O faturamento de cada linha é calculado assim:

```python
vendas["faturamento"] = (
    vendas["quantidade"] * vendas["preco_unitario"]
)
```

Para criar os resumos, usei `groupby()` e `agg()`. Na análise por loja, por
exemplo, o programa soma o faturamento e a quantidade e conta os pedidos
diferentes.

O ticket médio é:

```text
faturamento total / quantidade de pedidos
```

## 5. Criação do Excel

O Pandas envia cada análise para uma aba. Depois, o OpenPyXL aplica:

- Cores e títulos;
- Formato de moeda e data;
- Filtros;
- Congelamento do cabeçalho;
- Tabelas;
- Formatação condicional;
- Gráficos.

A aba `Resumo` reúne os quatro indicadores principais e dois gráficos.

## 6. Testes

Os testes cobrem as partes que teriam maior impacto caso parassem de
funcionar:

- Conversão de valores brasileiros;
- Separação de linhas inválidas;
- Remoção de duplicados;
- Cálculo do faturamento;
- Ordenação da análise por loja;
- Criação das abas e dos gráficos.
