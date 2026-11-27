# Relatório de Qualidade dos Dados — Sales Automation Engine V2

- **Data/hora da execução:** 26/11/2026 01:51:58
- **Pasta de entrada:** `dados/entrada`
- **Status da execução:** `SUCESSO`
- **Diagnóstico:** SUCESSO — Todos os arquivos foram aceitos, validados e reconciliados.

## 1. Resumo da Ingestão de Arquivos

| Métrica de Ingestão | Valor |
| --- | ---: |
| Arquivos CSV encontrados | 3 |
| Arquivos aceitos | 3 |
| Arquivos rejeitados integralmente | 0 |
| Total de registros recebidos (arquivos aceitos) | 42 |

### 1.1 Arquivos Aceitos

| Arquivo | Registros Lidos | Colunas Extras Ignoradas |
| --- | ---: | --- |
| `vendas_fevereiro.csv` | 14 | Nenhuma |
| `vendas_janeiro.csv` | 14 | Nenhuma |
| `vendas_marco.csv` | 14 | Nenhuma |

### 1.2 Arquivos Rejeitados Integralmente

Nenhum arquivo foi rejeitado integralmente nesta execução.

## 2. Resumo da Validação de Registros

| Indicador de Qualidade | Valor |
| --- | ---: |
| Total de registros recebidos (arquivos aceitos) | 42 |
| Registros válidos | 36 |
| Registros rejeitados (inconsistências) | 6 |
| Linhas com múltiplos problemas simultâneos | 0 |
| Taxa de registros rejeitados | 14,29% |
| Alertas de investigação (`Pedido + Produto` recorrente) | 0 |

## 3. Distribuição de Motivos de Inconsistência

| Motivo | Ocorrências |
| --- | ---: |
| Data inválida | 1 |
| Loja ausente | 1 |
| Pedido ausente | 1 |
| Preço ausente | 1 |
| Quantidade inválida (menor ou igual a zero) | 1 |
| Registro duplicado | 1 |

> **Nota de contagem:** Quando uma linha possui múltiplos erros simultâneos, todos os motivos são registrados na tabela acima e concatenados em `inconsistencias.csv`, mas a linha é contabilizada **uma única vez** no total de registros rejeitados e na reconciliação.

## 4. Conflitos de Cabeçalho de Pedido (`Data` / `Loja`)

- **Premissa adotada:** o identificador `Pedido` é considerado globalmente único em toda a base recebida. Portanto, um mesmo pedido não pode apresentar datas ou lojas divergentes entre linhas ou arquivos; quando isso ocorre, **todas** as linhas envolvidas são rejeitadas.
- **Pedidos com conflito de Data:** Nenhum
- **Pedidos com conflito de Loja:** Nenhum

## 5. Alertas de Investigação (`Pedido + Produto` com Atributos Distintos)

Por decisão de negócio, linhas válidas com mesmo `Pedido` e mesmo `Produto`, porém com preço, quantidade ou categoria distintos, **não** são rejeitadas automaticamente, pois podem representar itens legítimos de um mesmo pedido na ausência de um identificador único de linha (`ID_Item`). Elas são destacadas abaixo para revisão humana:

Nenhum alerta de investigação identificado nesta execução.

## 6. Política de Duplicatas e Limitação de Granularidade

- **Pedidos com múltiplos itens:** um mesmo `Pedido` com produtos diferentes, mesma `Data` e mesma `Loja` é tratado como venda legítima de múltiplos itens e contabilizado como **1 pedido distinto**.
- **Duplicatas exatas (política preservada da V1):** linhas integralmente idênticas nas 7 colunas de negócio normalizadas têm a primeira ocorrência mantida e as repetições seguintes rejeitadas como `Registro duplicado`.
- **Limitação documentada:** como os arquivos de entrada não possuem chave única de linha (`ID_Item`), a remoção de duplicatas exatas é uma regra operacional adotada para este conjunto de dados e não uma garantia universal de que duas compras idênticas nunca ocorreriam no mesmo pedido.
