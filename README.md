# Automação de relatório de vendas

Criei este projeto para praticar Python e análise de dados em uma situação
próxima de uma rotina de empresa: receber arquivos de vendas, organizar os
dados e gerar um relatório sem fazer o processo manualmente todo mês.

O programa lê arquivos CSV ou Excel, trata registros incorretos, calcula os
principais indicadores e entrega um arquivo `.xlsx` com tabelas e gráficos.

Os dados usados no projeto são fictícios.
Os arquivos de exemplo também possuem cinco linhas inválidas e uma duplicada
de propósito. Assim, é possível testar o tratamento de erros e conferir o
resultado na aba `Inconsistencias`.

## Funcionalidades

- Consolidação de vários arquivos em uma única base;
- Conversão de datas e valores no formato brasileiro;
- Remoção de registros duplicados;
- Separação de linhas com dados ausentes ou inválidos;
- Cálculo de faturamento e ticket médio;
- Análises por loja, produto, categoria e mês;
- Geração de relatório Excel formatado;
- Registro da execução em log;
- Testes automatizados das principais regras.

## Tecnologias utilizadas

- Python;
- Pandas;
- OpenPyXL;
- `unittest`.

## Estrutura do projeto

```text
.
├── dados/
│   └── entrada/                 # arquivos usados como entrada
├── docs/
│   └── como_funciona.md         # explicação das etapas
├── logs/                        # logs gerados durante a execução
├── resultado/                   # relatório Excel gerado
├── src/
│   └── relatorio_vendas.py      # tratamento, análises e exportação
├── tests/
│   └── test_relatorio_vendas.py
├── executar_projeto.cmd         # atalho para executar no Windows
├── main.py
└── requirements.txt
```

## Como executar

Requisito: Python 3.10 ou superior.

### 1. Crie um ambiente virtual

No Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No Linux ou macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 2. Gere o relatório

No Windows:

```powershell
.\.venv\Scripts\python.exe main.py
```

No Linux ou macOS:

```bash
.venv/bin/python main.py
```

O arquivo será salvo em `resultado/relatorio_vendas.xlsx`.

No Windows, depois de preparar o ambiente, também é possível usar o arquivo
`executar_projeto.cmd`.

Para escolher outros caminhos no Windows:

```powershell
.\.venv\Scripts\python.exe main.py `
    --entrada caminho/dos/arquivos `
    --saida caminho/relatorio.xlsx
```

## Formato dos arquivos de entrada

Os arquivos devem ser `.csv` ou `.xlsx` e conter estas colunas:

| Coluna | Exemplo |
|---|---|
| Data | 28/03/2026 |
| Pedido | P-3012 |
| Loja | Sul |
| Produto | Mouse Sem Fio |
| Categoria | Acessórios |
| Quantidade | 7 |
| Preço Unitário | 89,90 |

Os arquivos CSV do exemplo usam `;` como separador.

## Resultado com os dados de exemplo

| Indicador | Resultado |
|---|---:|
| Vendas válidas | 36 |
| Registros descartados | 6 |
| Pedidos | 36 |
| Itens vendidos | 120 |
| Faturamento | R$ 65.068,00 |
| Ticket médio | R$ 1.807,44 |

O relatório possui as abas `Resumo`, `Vendas_Limpas`, `Por_Loja`,
`Por_Produto`, `Por_Categoria`, `Por_Mes` e `Inconsistencias`.

## Testes

Para executar os testes:

No Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

No Linux ou macOS:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes verificam a conversão de valores, a limpeza dos dados, os
agrupamentos, a validação das colunas e a criação do arquivo Excel.

## O que pratiquei

- Leitura e concatenação de arquivos com Pandas;
- Limpeza de dados e tratamento de valores ausentes;
- Filtros, agrupamentos e funções de agregação;
- Organização do código em funções;
- Geração e formatação de planilhas;
- Criação de testes automatizados.

Uma explicação mais detalhada está em
[docs/como_funciona.md](docs/como_funciona.md).

## Limitações atuais

- Os arquivos CSV precisam usar `;` como separador;
- Os nomes das colunas precisam seguir o formato documentado;
- Os dados são processados em memória;
- O relatório é gerado localmente e não possui agendamento automático.

Mantive essas limitações para não aumentar demais o escopo da primeira versão.

## Próximas melhorias

- Salvar a base tratada em SQLite;
- Permitir nomes alternativos para as colunas;
- Adicionar uma meta mensal e calcular a diferença para o resultado.

## Arquivos gerados

O relatório e o log não ficam versionados no Git. Eles são recriados sempre
que o programa é executado. Os arquivos `.gitkeep` servem apenas para manter as
pastas `resultado` e `logs` visíveis no repositório.
