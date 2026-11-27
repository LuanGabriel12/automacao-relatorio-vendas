# Relatório de Reconciliação Matemática — Sales Automation Engine V2

- **Data/hora da execução:** 26/11/2026 01:51:58
- **Status da execução:** `SUCESSO`
- **Veredito da reconciliação:** **APROVADA** (11/11 verificações aprovadas)
- **Escopo dos registros reconciliados:** apenas os `3` arquivo(s) aceito(s). Arquivos rejeitados integralmente (`0`) são contabilizados separadamente para evitar distorção nas contagens de linhas.

## 1. Matriz de Verificações Matemáticas

| Código | Verificação | Fórmula | Esperado | Obtido | Diferença | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `REC-01` | Registros consolidados vs. soma dos arquivos aceitos | `len(dados_brutos) == sum(registros_lidos nos arquivos aceitos)` | 42 | 42 | 0 | **APROVADA** |
| `REC-02` | Equação fundamental de registros (Recebidos = Válidos + Rejeitados) | `total_registros_recebidos == len(vendas_validas) + len(inconsistencias)` | 42 | 42 | 0 | **APROVADA** |
| `REC-03` | Faturamento consolidado (recálculo independente linha a linha) | `sum(Decimal(Quantidade) * Preço Unitário) == kpis['faturamento_total']` | 65068,00 | 65068,00 | 0,00 | **APROVADA** |
| `REC-04` | Faturamento agrupado por loja vs. consolidado | `sum(analise_lojas['Faturamento']) == faturamento_total` | 65068,00 | 65068,00 | 0,00 | **APROVADA** |
| `REC-05` | Faturamento agrupado por produto vs. consolidado | `sum(analise_produtos['Faturamento']) == faturamento_total` | 65068,00 | 65068,00 | 0,00 | **APROVADA** |
| `REC-06` | Faturamento agrupado por categoria vs. consolidado | `sum(analise_categorias['Faturamento']) == faturamento_total` | 65068,00 | 65068,00 | 0,00 | **APROVADA** |
| `REC-07` | Faturamento agrupado por mês vs. consolidado | `sum(analise_mensal['Faturamento']) == faturamento_total` | 65068,00 | 65068,00 | 0,00 | **APROVADA** |
| `REC-08` | Unidades vendidas (base vs. loja, produto, categoria e mês) | `unidades_totais == sum(lojas) == sum(produtos) == sum(categorias) == sum(mensal)` | 120 | 120 | 0 | **APROVADA** |
| `REC-09` | Pedidos distintos (base vs. soma por loja e por mês) | `nunique(Pedido) == sum(lojas['Pedidos']) == sum(mensal['Pedidos'])` | 36 | 36 | 0 | **APROVADA** |
| `REC-10` | Soma das participações percentuais (lojas, produtos, categorias e meses) | `sum(Participação (%)) == 100% em todas as dimensões` | 100,00 | 100,00 | 0,00 | **APROVADA** |
| `REC-11` | Consistência de Ticket Médio e Receita por Unidade (razão entre totais) | `ticket_medio == faturamento / pedidos e receita_unid == faturamento / unidades` | 1807,444444 | 1807,444444 | 0,00 | **APROVADA** |

## 2. Auditoria de Precisão Monetária (`Decimal` vs. `float64`)

Todos os valores monetários da V2 são construídos diretamente em `Decimal` a partir das strings normalizadas dos CSVs, sem conversão intermediária para `float`, garantindo tolerância zero (`0,00`) na reconciliação.

| Critério de Precisão | Resultado Observado |
| --- | --- |
| Faturamento consolidado em `Decimal` exato | `R$ 65.068,00` (`65068.00`) |
| Soma equivalente em `float64` (apenas auditoria) | `65068.00000000001` |
| Diferença absoluta `float64` vs. `Decimal` no total | `0.00000000001` |
| Linhas com ruído binário em `float64` (`Qtd * Preço`) | `5` |

## 3. Nota sobre Aditividade de Pedidos nas Agregações

- **Por Loja e por Mês (`REC-09`):** a soma de `Pedidos` é aditiva e igual ao total de pedidos distintos, pois a regra de unicidade global de `Pedido` impede que um mesmo pedido exista em duas lojas ou duas datas distintas.
- **Por Produto e por Categoria:** em pedidos com múltiplos itens de produtos/categorias diferentes, o mesmo `Pedido` aparece legitimamente em mais de um produto ou categoria; por isso, a contagem de `Pedidos` nessas duas dimensões **não** é somável ao total consolidado.
