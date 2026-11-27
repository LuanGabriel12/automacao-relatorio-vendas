# Dicionário de Dados — Sales Automation Engine V2

Este documento descreve o esquema dos arquivos de entrada e de todos os 11 arquivos gerados pela V2, incluindo tipos, formatos brasileiros, regras de construção e compatibilidade com Power BI.

---

## 1. Arquivos de Entrada (`dados/entrada/*.csv`)

- **Formato:** CSV UTF-8 (também aceita UTF-8 com BOM), separador `;`, quebra de linha `LF` (`\n`), separador decimal `,`, separador de milhar `.` (em grupos exatos de 3 dígitos) e datas `DD/MM/AAAA`.
- **Base original preservada (V1):** `vendas_janeiro.csv`, `vendas_fevereiro.csv` e `vendas_marco.csv` (`14` linhas de dados cada, `42` no total; dados 100% fictícios).

| Coluna Obrigatória | Tipo de Negócio Esperado | Exemplo Válido | Regras de Aceitação |
| --- | --- | --- | --- |
| `Data` | Data (`DD/MM/AAAA`) | `05/01/2026` | Obrigatória; deve representar data real de calendário. |
| `Pedido` | Texto (identificador) | `P-1001` | Obrigatório; globalmente único em termos de cabeçalho (`Data` e `Loja`). |
| `Loja` | Texto | `Centro` | Obrigatório; espaços nas pontas são normalizados em `vendas_tratadas.csv`. |
| `Produto` | Texto | `Notebook Pro 14` | Obrigatório; pode repetir no mesmo `Pedido` (ver regra de alertas). |
| `Categoria` | Texto | `Informática` | Obrigatório; usado em agrupamentos e participações. |
| `Quantidade` | Inteiro positivo (`> 0`) | `3` ou `1.000` | Obrigatório; deve ser inteiro `> 0` (rejeita `0`, negativos, frações `1,5` e textos). |
| `Preço Unitário` | Monetário `Decimal` (`> 0`) | `3.499,90` ou `89,90` | Obrigatório; deve ser número brasileiro válido, finito e `> 0`. |

> **Colunas extras na entrada:** caso algum CSV possua colunas adicionais além das 7 obrigatórias, o arquivo é aceito e os nomes das colunas extras ignoradas são registrados no `relatorio_qualidade.md` e no `resumo_execucao.json`.

---

## 2. Arquivos de Saída (`resultado/`)

Todos os CSVs de saída são gravados em **UTF-8**, terminação **`LF` (`\n`)**, separador **`;`** e separador decimal **`,`**, sem pontos de milhar — formato pronto para importação direta no **Power BI Desktop** (definindo localidade `Português (Brasil)` nas colunas decimais e de data).

### 2.1 `vendas_tratadas.csv` (Tabela Fato Limpa)
Granularidade: **1 linha por item de venda validado** (ordenada cronologicamente por `Data`, `Pedido`, `Produto`, `Arquivo de origem`, `Linha no arquivo`).

| Coluna | Tipo Lógico | Formato no CSV | Descrição |
| --- | --- | --- | --- |
| `Data` | Data | `DD/MM/AAAA` | Data validada da venda. |
| `Ano_Mes` | Texto | `AAAA-MM` | Chave mensal de ordenação e agrupamento temporal (ex.: `2026-01`). |
| `Pedido` | Texto | `P-1001` | Identificador normalizado do pedido. |
| `Loja` | Texto | `Centro` | Nome normalizado da loja/canal. |
| `Produto` | Texto | `Notebook Pro 14` | Nome normalizado do produto. |
| `Categoria` | Texto | `Informática` | Categoria comercial normalizada. |
| `Quantidade` | Inteiro | `2` | Unidades vendidas na linha (`> 0`). |
| `Preço Unitário` | Decimal exato | `3499,90` | Preço unitário exato (sem ruído `float64`). |
| `Faturamento` | Decimal exato | `6999,80` | `Quantidade * Preço Unitário` em `Decimal` exato. |
| `Arquivo de origem` | Texto | `vendas_janeiro.csv` | Nome do CSV de origem para rastreabilidade. |
| `Linha no arquivo` | Inteiro | `2` | Número exato da linha no CSV original (cabeçalho = linha 1). |

> **Evolução frente à V1:** as colunas redundantes `Data informada`, `Motivo` (sempre vazia em válidas) e `Status` (sempre `"Válido"`) foram removidas de `vendas_tratadas.csv` para entregar uma tabela fato limpa para análise e Power BI; a coluna `Mês` foi padronizada como `Ano_Mes` e foi adicionada `Linha no arquivo`.

### 2.2 `inconsistencias.csv` (Tabela de Auditoria de Rejeições)
Preserva integralmente os **valores brutos originais** das 7 colunas de entrada (sem alteração silenciosa), acrescidos de rastreabilidade:

| Coluna | Descrição |
| --- | --- |
| `Data`, `Pedido`, `Loja`, `Produto`, `Categoria`, `Quantidade`, `Preço Unitário` | Valores brutos exatamente como lidos do arquivo CSV original (ex.: `31/02/2026`, `-2`, `1,5`, `inf`, `""`). |
| `Arquivo de origem` | Nome do arquivo CSV de origem. |
| `Linha no arquivo` | Linha exata no arquivo original para correção na fonte. |
| `Quantidade de problemas` | Quantidade de regras violadas simultaneamente naquela linha (`>= 1`). |
| `Motivo` | Lista de todos os motivos detectados na linha, separados por `; `. |
| `Status` | Valor fixo `"Inválido"`. |

### 2.3 `kpis_executivos.csv`
| Coluna | Descrição |
| --- | --- |
| `Indicador` | Nome do indicador executivo (11 linhas). |
| `Valor` | Valor calculado em `Decimal`/inteiro (formato brasileiro `,` sem ponto de milhar). |
| `Unidade` | Unidade de medida (`registros`, `%`, `pedidos`, `unidades`, `R$`, `R$/pedido`, `R$/unidade`, `unidades/pedido`, `linhas/pedido`). |
| `Formula` | Definição explícita do cálculo aplicado. |

### 2.4 `analise_lojas.csv`, `analise_produtos.csv`, `analise_categorias.csv` e `analise_mensal.csv`
- **`analise_lojas.csv`:** `Ranking`, `Loja`, `Registros`, `Pedidos`, `Quantidade`, `Faturamento`, `Ticket Médio`, `Receita por Unidade`, `Participação (%)`.
- **`analise_produtos.csv`:** `Ranking`, `Produto`, `Categoria`, `Registros`, `Pedidos`, `Quantidade`, `Faturamento`, `Receita por Unidade`, `Participação (%)`.
- **`analise_categorias.csv`:** `Ranking`, `Categoria`, `Registros`, `Pedidos`, `Produtos Distintos`, `Quantidade`, `Faturamento`, `Receita por Unidade`, `Participação (%)`.
- **`analise_mensal.csv`:** `Ano_Mes`, `Registros`, `Pedidos`, `Quantidade`, `Faturamento`, `Ticket Médio`, `Receita por Unidade`, `Participação (%)`, `Faturamento Período Anterior`, `Variação Faturamento (R$)`, `Variação Faturamento (%)`, `Variação Unidades (%)`.

### 2.5 Relatórios e Resumo Estruturado
- **`relatorio_qualidade.md`:** ingestão (aceitos vs. rejeitados), resumo de validação, motivos, conflitos de cabeçalho e alertas de investigação `Pedido + Produto`.
- **`relatorio_reconciliacao.md`:** matriz completa das 11 verificações matemáticas (`REC-01` a `REC-11`) e auditoria `Decimal` vs. `float64`.
- **`relatorio_executivo.md`:** KPIs, rankings, evolução mensal e síntese empresarial baseada exclusivamente nos dados processados.
- **`resumo_execucao.json`:** resumo estruturado para consumo automatizado (`timestamp_execucao`, `duracao_segundos`, `status_execucao`, `flags`, `ingestao`, `qualidade`, `kpis`, `reconciliacao`, `arquivos_gerados`).
