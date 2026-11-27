# Cenários Sintéticos de Demonstração

Todos os arquivos neste diretório (`dados/exemplos/`) são **100% sintéticos**, criados exclusivamente para demonstrar e validar o comportamento do **Sales Automation Engine V2** em situações reais de qualidade de dados e controle operacional. Os arquivos originais da V1 permanecem preservados intactos em `dados/entrada/`.

| Pasta do Cenário | Situação Testada | Resultado Esperado |
| --- | --- | --- |
| `cenario_valido/` | 3 registros válidos, 0 erros | `SUCESSO`, 3 válidos, 0 inconsistências, R$ 5.700,00 |
| `cenario_registros_invalidos/` | Data inválida, quantidade negativa/zero/fracionada, preço malformado (`12.34`), `inf`, `NaN`, múltiplos erros na mesma linha | `SUCESSO`, 1 válido (`S-2001`, R$ 180,00), 5 inconsistências sem dupla contagem |
| `cenario_duplicatas/` | Duplicata exata no mesmo arquivo (`S-3001`) e entre arquivos (`S-3002`) | `SUCESSO`, 3 válidos, 2 duplicatas rejeitadas |
| `cenario_multiplos_itens/` | `S-4001` com 3 produtos distintos (1 pedido) e `S-4002` com mesmo produto e preço/qtd distintos | `SUCESSO`, 5 válidos, 2 pedidos distintos, 1 alerta de investigação (`S-4002 + SSD 1TB`) |
| `cenario_arquivo_vazio/` | 1 CSV válido + 1 CSV 0 bytes + 1 CSV apenas cabeçalho | `CONCLUIDO_PARCIALMENTE` (alerta explícito de arquivos rejeitados) |
| `cenario_sem_colunas_obrigatorias/` | 1 CSV válido + 1 CSV sem `Categoria` e `Preço Unitário` | `CONCLUIDO_PARCIALMENTE` (alerta explícito de arquivo rejeitado) |
| `cenario_sem_vendas_validas/` | 1 CSV válido estruturalmente, porém com todas as 3 linhas inválidas | `CONCLUIDO_SEM_VENDAS_VALIDAS`, 0 vendas válidas, sem `ZeroDivisionError` |
| `cenario_conflito_entre_arquivos/` | `S-8001` com `Data` conflitante e `S-8002` com `Loja` conflitante entre dois arquivos | `SUCESSO`, apenas `S-8003` válido (R$ 200,00); todas as 4 linhas conflitantes rejeitadas |
