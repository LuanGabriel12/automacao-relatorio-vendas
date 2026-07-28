# Análise de vendas com Python

Criei este projeto para praticar análise de dados em uma situação próxima de
uma rotina de vendas. O programa reúne dados de três meses, separa linhas com
problemas, calcula indicadores e gera tabelas de resumo e gráficos.

O código está em um único arquivo e segue uma ordem linear, o que facilita o
estudo de cada etapa. Todos os dados usados no projeto são fictícios.

## O que o projeto faz

- Lê três arquivos CSV com Pandas;
- Junta os meses em uma única tabela;
- Identifica campos ausentes, datas inválidas, valores menores ou iguais a
  zero e registros duplicados;
- Calcula faturamento, ticket médio e quantidade de itens;
- Cria análises por loja, produto e mês;
- Salva cinco tabelas em CSV;
- Gera um gráfico em PNG com Matplotlib.

## Tecnologias utilizadas

- Python;
- Pandas;
- NumPy;
- Matplotlib;
- `datetime`, que já faz parte do Python.

## Resultado validado com os dados de exemplo

| Indicador | Resultado |
|---|---:|
| Vendas válidas | 36 |
| Inconsistências | 6 |
| Pedidos | 36 |
| Itens vendidos | 120 |
| Faturamento | R$ 65.068,00 |
| Ticket médio | R$ 1.807,44 |

![Gráficos com o resumo das vendas](docs/resumo_vendas.png)

## Como executar

O projeto foi testado com Python 3.12.

No Windows, abra o PowerShell dentro da pasta do projeto e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Depois da primeira configuração, também é possível executar o arquivo
`executar_projeto.cmd`.

Os resultados serão criados na pasta `resultado`.

## Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `resultado/vendas_tratadas.csv` | Vendas que passaram pela validação |
| `resultado/inconsistencias.csv` | Linhas que precisam ser corrigidas |
| `resultado/analise_lojas.csv` | Quantidade e faturamento por loja |
| `resultado/analise_produtos.csv` | Quantidade e faturamento por produto |
| `resultado/analise_mensal.csv` | Quantidade e faturamento por mês |
| `resultado/resumo_vendas.png` | Gráficos de faturamento |

## Estrutura

```text
.
├── dados/
│   └── entrada/              # arquivos CSV usados na análise
├── docs/
│   ├── como_funciona.md      # explicação da lógica
│   └── resumo_vendas.png     # exemplo do gráfico gerado
├── resultado/                # arquivos criados pelo programa
├── .gitattributes
├── .gitignore
├── executar_projeto.cmd
├── main.py                   # código do projeto
└── requirements.txt
```

## Formato dos dados

Os arquivos de entrada usam `;` como separador e precisam ter estas colunas:

| Coluna | Exemplo |
|---|---|
| Data | 28/03/2026 |
| Pedido | P-3012 |
| Loja | Sul |
| Produto | Mouse Sem Fio |
| Categoria | Acessórios |
| Quantidade | 7 |
| Preço Unitário | 89,90 |

O conjunto de exemplo contém cinco linhas com campos inválidos e um registro
repetido. Esses casos permitem conferir o resultado da validação.

## O que pratiquei

- `read_csv()` e `concat()` para leitura e união dos dados;
- Tratamento de datas e valores ausentes;
- Filtros com `loc`;
- Cálculos entre colunas;
- `groupby()` para resumir os resultados;
- Criação de gráficos com Matplotlib;
- Exportação de DataFrames para CSV.

A ordem completa das etapas está em
[docs/como_funciona.md](docs/como_funciona.md).

## Limitações atuais

- Os três nomes de arquivo estão escritos no começo do `main.py`;
- Os arquivos precisam ser CSV e usar `;` como separador;
- Os nomes das colunas precisam seguir o modelo deste projeto;
- O programa deve ser executado a partir da pasta do projeto.
- Quando uma linha tem mais de um problema, é mostrado o primeiro encontrado
  na ordem das validações.

Uma próxima versão pode procurar novos arquivos automaticamente e separar o
código em funções. Nesta versão, mantive o foco nos conceitos que estou
praticando.
