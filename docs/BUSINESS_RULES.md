# Regras de Negócio e Fórmulas — Sales Automation Engine V2

Este documento formaliza todas as regras de negócio, premissas de granularidade, fórmulas de indicadores e critérios de reconciliação adotados na V2.

---

## 1. Granularidade e Premissas de Identidade

1. **Granularidade da tabela fato (`vendas_tratadas.csv`):** cada linha representa **um item vendido dentro de um pedido**. Um mesmo pedido pode conter múltiplos itens (várias linhas).
2. **Premissa de unicidade global de `Pedido`:** assume-se que o identificador `Pedido` é globalmente único em toda a pasta de entrada processada. Por consequência:
   - Um mesmo `Pedido` com mesma `Data`, mesma `Loja` e **produtos diferentes** é um **pedido legítimo com múltiplos itens** (todas as linhas permanecem válidas e contam como **1 pedido distinto**).
   - Um mesmo `Pedido` com **`Data` ou `Loja` divergentes** entre linhas ou arquivos caracteriza **conflito de cabeçalho**, e **todas as linhas envolvidas** são rejeitadas para não escolher arbitrariamente qual origem prevalece.
3. **Mesmo `Pedido + Produto` com atributos distintos (preço, quantidade ou categoria):** **não** é rejeitado automaticamente como conflito, pois pode refletir itens legítimos de um pedido (ex.: lote promocional + lote padrão). Essas ocorrências permanecem válidas e são sinalizadas como **alertas de investigação** devido à ausência de um identificador único de linha (`ID_Item`).
4. **Política de duplicatas exatas (preservada da V1):** registros integralmente idênticos nas 7 colunas normalizadas (`Data`, `Pedido`, `Loja`, `Produto`, `Categoria`, `Quantidade`, `Preço Unitário`) têm a 1ª ocorrência mantida e as demais rejeitadas como `Registro duplicado`. Esta é uma regra operacional adotada para este conjunto de dados, não uma garantia universal.

---

## 2. Regras de Validação Numérica e Monetária

- **Quantidade:** número **inteiro estritamente maior que zero** (`> 0`). Rejeita zeros, negativos, frações (`1,5`, `2,0`), strings malformadas e infinitos (`inf`, `NaN`).
- **Preço Unitário:** número brasileiro válido, finito e **estritamente maior que zero** (`> 0`), construído diretamente em `Decimal` a partir da string normalizada (sem passagem intermediária por `float`).
- **Regra estrita do formato brasileiro:** ponto `.` só é aceito como separador de milhar em grupos exatos de 3 dígitos (ex.: `3.499,90` -> `Decimal("3499.90")`). Formatos ambíguos como `12.34` são rejeitados em vez de convertidos silenciosamente em `1234`.

---

## 3. Fórmulas dos Indicadores Comerciais

Todos os indicadores de razão são calculados como **divisão entre totais** (jamais média de médias). Quando não houver vendas válidas (`0` pedidos ou `0` unidades), indicadores de razão retornam `0,00` de forma controlada.

| Indicador | Fórmula Matemática | Observação |
| --- | --- | --- |
| **Faturamento da Linha** | $\text{Quantidade} \times \text{Preço Unitário}$ | Calculado em `Decimal` exato. |
| **Faturamento Total** | $\sum \text{Faturamento da Linha}$ | Soma exata em `Decimal`. |
| **Registros Válidos** | Contagem de linhas válidas | Diferente de pedidos e de unidades. |
| **Pedidos Distintos** | Contagem distinta (`nunique`) de `Pedido` | Protege contra contagem dupla em pedidos multi-item. |
| **Unidades Vendidas** | $\sum \text{Quantidade}$ | Volume físico total comercializado. |
| **Ticket Médio por Pedido** | $\frac{\text{Faturamento Total}}{\text{Pedidos Distintos}}$ | Razão de totais (nunca média dos preços ou linhas). |
| **Receita por Unidade** | $\frac{\text{Faturamento Total}}{\text{Unidades Vendidas}}$ | Preço médio ponderado realizado por unidade. |
| **Participação (%)** | $\frac{\text{Faturamento do Grupo}}{\text{Faturamento Total}} \times 100$ | Calculada por loja, produto, categoria e mês. |
| **Variação Mensal (R$)** | $\text{Fat}_{t} - \text{Fat}_{t-1}$ | Vazia (`None`) no primeiro período da série. |
| **Variação Mensal (%)** | $\frac{\text{Fat}_{t} - \text{Fat}_{t-1}}{\text{Fat}_{t-1}} \times 100$ | Comparação período a período sobre meses ordenados. |
| **Taxa de Rejeição (%)** | $\frac{\text{Registros Rejeitados}}{\text{Registros Recebidos}} \times 100$ | Calculada sobre registros de arquivos aceitos. |

> **Escopo financeiro honesto:** o projeto **não** calcula lucro comercial nem margem de lucro porque os arquivos de entrada não contêm dados de custo.

---

## 4. Critérios de Ranking e Aditividade

- **Desempate determinístico nos rankings:**
  - Lojas: `Faturamento` decrescente -> `Quantidade` decrescente -> `Loja` crescente.
  - Produtos: `Faturamento` decrescente -> `Quantidade` decrescente -> `Produto` crescente -> `Categoria` crescente.
  - Categorias: `Faturamento` decrescente -> `Quantidade` decrescente -> `Categoria` crescente.
- **Aditividade de `Pedidos`:**
  - `Pedidos` é **aditivo** por `Loja` e por `Ano_Mes` (a soma dos grupos iguala o total consolidado de pedidos distintos), graças à premissa de cabeçalho único por `Pedido`.
  - `Pedidos` é **não aditivo** por `Produto` e por `Categoria`, pois um pedido multi-item pode conter produtos de categorias diferentes.

---

## 5. Regras da Reconciliação Obrigatória (`REC-01` a `REC-11`)

Uma execução só pode ser exportada se **todas as 11 verificações** passarem com diferença `0` em contagens e `0,00` em valores monetários (`Decimal`):

1. `REC-01`: `len(dados_brutos) == sum(registros_lidos nos arquivos aceitos)`
2. `REC-02`: `total_registros_recebidos == len(vendas_validas) + len(inconsistencias)`
3. `REC-03`: recálculo independente linha a linha `sum(Decimal(Quantidade) * Preço Unitário) == faturamento_total`
4. `REC-04`: `sum(analise_lojas["Faturamento"]) == faturamento_total`
5. `REC-05`: `sum(analise_produtos["Faturamento"]) == faturamento_total`
6. `REC-06`: `sum(analise_categorias["Faturamento"]) == faturamento_total`
7. `REC-07`: `sum(analise_mensal["Faturamento"]) == faturamento_total`
8. `REC-08`: unidades vendidas idênticas entre base, lojas, produtos, categorias e meses
9. `REC-09`: pedidos distintos idênticos entre base, soma por loja e soma por mês
10. `REC-10`: soma exata das participações percentuais igual a `100%` (quando há faturamento `> 0`)
11. `REC-11`: `ticket_medio == faturamento / pedidos` e `receita_por_unidade == faturamento / unidades`
