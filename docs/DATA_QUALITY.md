# Qualidade dos Dados — Sales Automation Engine V2

Este documento detalha os controles de qualidade implementados nas camadas de ingestão (`src/data/loader.py`), validação (`src/data/validation.py`) e limpeza (`src/data/cleaning.py`), além dos achados reais nos dados originais da V1.

---

## 1. Arquitetura de Qualidade em Duas Barreiras

### Barreira 1 — Qualidade Estrutural de Arquivo (`loader.py`)
Antes de qualquer linha entrar na consolidação, cada CSV individual é validado estruturalmente:

| Falha Estrutural Detectada | Motivo Registrado | Impacto |
| --- | --- | --- |
| Arquivo com 0 bytes | `Arquivo vazio (0 bytes, sem cabeçalho nem dados)` | Arquivo rejeitado integralmente |
| Apenas cabeçalho (0 linhas de dados) | `Arquivo vazio (apenas cabeçalho, sem registros de vendas)` | Arquivo rejeitado integralmente |
| Codificação não UTF-8 | `Erro de codificação na leitura (esperado UTF-8)` | Arquivo rejeitado integralmente |
| CSV corrompido (`ParserError`) | `Erro de estrutura/formatação CSV na leitura do arquivo` | Arquivo rejeitado integralmente |
| Cabeçalho com coluna sem nome (ex.: `;` sobrando no final) | `Cabeçalho inválido: coluna sem nome detectada` | Arquivo rejeitado integralmente |
| Cabeçalho com nomes duplicados ou ambíguos (ex.: duas colunas `Preço Unitário`) | `Cabeçalho inválido: colunas duplicadas ou ambíguas (...)` | Arquivo rejeitado integralmente |
| Linhas com mais colunas que o cabeçalho (deslocamento de índice) | `Erro de estrutura CSV: linhas contêm mais colunas do que o cabeçalho` | Arquivo rejeitado integralmente |
| Ausência de uma ou mais das 7 colunas obrigatórias | `Colunas obrigatórias ausentes: ... (verifique também se o separador é ';')` | Arquivo rejeitado integralmente |

> **Separação rigorosa de contagens:** arquivos rejeitados integralmente **não** entram em `total_registros_recebidos`, impedindo contagens enganosas na reconciliação. Além disso, qualquer arquivo rejeitado impede que a execução receba status `SUCESSO` (passando para `CONCLUIDO_PARCIALMENTE`).

### Barreira 2 — Qualidade de Registro (`validation.py`)
Cada linha dos arquivos aceitos passa por 5 etapas ordenadas sem alterar os valores originais:

1. **Validação de campos por linha (acumulativa):** testa todos os 7 campos independentemente e acumula todos os motivos encontrados na mesma linha, evitando o mascaramento da V1.
   - `Data`: ausente ou impossível no calendário (ex.: `31/02/2026`, formato `AAAA-MM-DD`).
   - `Pedido`, `Loja`, `Produto`, `Categoria`: ausentes ou contendo apenas espaços.
   - `Quantidade`: ausente, formato não inteiro/malformado (`1,5`, `2,0`, `12.34`, `abc`, `inf`, `NaN`, `1e3`, `1_000`) ou `<= 0`. Os inteiros convertidos são armazenados em `dtype="object"` para evitar que o Pandas converta `[int, None]` para `float64`, preservando precisão exata mesmo acima de $2^{53}$ (ex.: `9007199254740993`).
   - `Preço Unitário`: ausente, formato brasileiro malformado (`12.34`, `1..000`, `01.000`, `R$ 89,90`, `1,2,3`, `inf`, `-Infinity`, `NaN`, `1e2`) ou `<= 0`.
2. **Conflitos de cabeçalho de pedido entre linhas/arquivos:** sob a premissa documentada de que `Pedido` é globalmente único, se um mesmo `Pedido` aparecer com mais de uma `Data` válida ou mais de uma `Loja` preenchida, **todas as linhas** daquele pedido são rejeitadas (`Pedido conflitante (Data divergente)` e/ou `Pedido conflitante (Loja divergente)`).
3. **Duplicatas exatas (política preservada da V1):** entre registros que passaram nas etapas 1 e 2, linhas integralmente idênticas nas 7 colunas normalizadas mantêm a 1ª ocorrência e têm as repetições rejeitadas como `Registro duplicado`.
4. **Classificação sem NumPy:** cria `Motivo`, `Quantidade de problemas` e `Status` (`Válido`/`Inválido`) com atribuição booleana via `.loc`.
5. **Alertas de investigação (`Pedido + Produto`):** entre registros válidos, identifica pares `(Pedido, Produto)` recorrentes com preço, quantidade ou categoria distintos. Eles **permanecem válidos**, mas ficam destacados em `relatorio_qualidade.md` e `resumo_execucao.json`.

---

## 2. Múltiplos Problemas na Mesma Linha sem Dupla Contagem

Na V1, uma linha com `Data = 31/02/2026`, `Quantidade = -1` e `Preço Unitário = 12.34` recebia apenas `Data inválida`, escondendo os outros dois erros.

Na V2:
- `Motivo` registra: `Data inválida; Quantidade inválida (menor ou igual a zero); Preço inválido (formato inválido ou não finito)`.
- `Quantidade de problemas` registra `3`.
- Em `relatorio_qualidade.md`, a tabela de distribuição por motivo soma cada tipo de ocorrência (para priorização corretiva), enquanto `total_registros_rejeitados` e a reconciliação (`REC-02`) contam essa linha **exatamente 1 vez**.

---

## 3. Auditoria de Qualidade na Base Original (`dados/entrada/`)

| Arquivo | Linha | Pedido | Valor Problemático Original | Motivo Registrado pela V2 |
| --- | ---: | --- | --- | --- |
| `vendas_fevereiro.csv` | 14 | `P-2013` | `Quantidade = -2` | `Quantidade inválida (menor ou igual a zero)` |
| `vendas_fevereiro.csv` | 15 | `P-2014` | `Preço Unitário = ""` | `Preço ausente` |
| `vendas_janeiro.csv` | 14 | `P-1002` | Cópia integral da linha 3 | `Registro duplicado` |
| `vendas_janeiro.csv` | 15 | `P-1013` | `Loja = ""` | `Loja ausente` |
| `vendas_marco.csv` | 14 | `P-3013` | `Data = 31/02/2026` | `Data inválida` |
| `vendas_marco.csv` | 15 | *(vazio)* | `Pedido = ""` | `Pedido ausente` |

- **Total recebido:** `42` | **Válidos:** `36` | **Rejeitados:** `6` (`14,29%`) | **Conflitos de cabeçalho:** `0` | **Alertas `Pedido + Produto`:** `0`.
- **Auditoria de ruído `float64`:** a V2 detectou que `5` das `36` linhas válidas geravam ruído binário em `float64` (ex.: `3 * 89,90 -> 269,70000000000005` na V1), levando a uma diferença total de `0.00000000001` na soma em `float64` — completamente eliminada pelo uso de `Decimal`.

---

## 4. Limitações de Qualidade Documentadas

1. **Ausência de identificador único de linha (`ID_Item`):** sem uma chave primária de item de pedido, não é matematicamente possível provar com 100% de certeza se duas linhas idênticas foram duplicadas na exportação ou compradas separadamente no mesmo pedido. A remoção de duplicatas exatas é uma política operacional adotada para este conjunto.
2. **Ausência de cadastro mestre (dimensões de referência):** não existe tabela oficial de lojas, produtos ou tabela de preços para validar se um preço unitário está dentro de faixa comercial ou se um nome de produto possui erro de digitação (ex.: `"Mouse sem fio"` vs. `"Mouse Sem Fio"`).
3. **Datas futuras/passadas:** qualquer data de calendário válida em `DD/MM/AAAA` é aceita; regras de janela fiscal específica exigiriam parâmetros externos de período contábil.
