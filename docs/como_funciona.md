# Como o código funciona

O `main.py` é executado de cima para baixo. Não existem classes nem funções
criadas por mim nessa versão. A lógica está dividida em etapas.

## 1. Leitura

A lista `arquivos` guarda o caminho dos três CSVs. O `for` lê um arquivo de
cada vez com:

```python
pd.read_csv(arquivo, sep=";", decimal=",", thousands=".")
```

- `sep=";"` informa qual é o separador das colunas;
- `decimal=","` reconhece a vírgula dos centavos;
- `thousands="."` reconhece o ponto usado nos milhares.

Cada tabela entra na lista `tabelas`. Depois, o `pd.concat()` junta os três
meses em um único DataFrame chamado `vendas`.

## 2. Tratamento das datas

O Pandas converte a coluna de datas:

```python
vendas["Data"] = pd.to_datetime(
    vendas["Data"],
    format="%d/%m/%Y",
    errors="coerce",
)
```

O formato informa que a ordem é dia, mês e ano. Com `errors="coerce"`, uma
data impossível, como 31/02/2026, vira um valor vazio. Assim ela pode ser
encontrada na validação.

## 3. Validação

A coluna `Motivo` começa vazia. Os filtros com `.loc` procuram problemas e
escrevem o motivo correspondente:

- Data inválida;
- Pedido, loja, produto ou categoria ausente;
- Quantidade menor ou igual a zero;
- Preço ausente ou menor que zero;
- Registro duplicado.

O NumPy cria a coluna `Status`:

```python
vendas["Status"] = np.where(
    vendas["Motivo"] == "",
    "Válido",
    "Inválido",
)
```

Se o motivo estiver vazio, a venda é válida. Caso exista um motivo, ela é
inválida.

## 4. Separação

Dois filtros criam tabelas diferentes:

```python
vendas_validas = vendas.loc[vendas["Status"] == "Válido"].copy()
inconsistencias = vendas.loc[vendas["Status"] == "Inválido"].copy()
```

Isso mantém as linhas com problema disponíveis para revisão, em vez de
apagá-las sem explicação.

## 5. Cálculos

O faturamento de cada linha é a quantidade multiplicada pelo preço:

```python
vendas_validas["Faturamento"] = (
    vendas_validas["Quantidade"] * vendas_validas["Preço Unitário"]
)
```

Depois são calculados:

- Faturamento total;
- Total de itens vendidos;
- Quantidade de pedidos diferentes;
- Ticket médio, dividindo o faturamento pela quantidade de pedidos.

## 6. Agrupamentos

O `groupby()` reúne as linhas que possuem a mesma loja, produto ou mês. O
`.sum()` soma a quantidade e o faturamento de cada grupo.

Na análise por loja, o `.sort_values()` coloca primeiro a loja com maior
faturamento. O `.reset_index()` transforma o nome da loja novamente em uma
coluna comum.

## 7. Arquivos e gráficos

O `.to_csv()` salva as tabelas na pasta `resultado`. Usei `;` como separador
e `,` nos valores decimais para manter o padrão brasileiro.

O Matplotlib cria:

- Um gráfico de barras com o faturamento por loja;
- Um gráfico de linha com o faturamento por mês.

O `datetime.now()` coloca no título a data e a hora da execução. No final, o
gráfico é salvo como `resultado/resumo_vendas.png`.
