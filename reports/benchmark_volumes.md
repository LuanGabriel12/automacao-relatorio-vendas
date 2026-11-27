# Medição Real de Comportamento por Volume — Sales Automation Engine V2

- **Data/hora da medição:** 26/11/2026 01:51:58
- **Ambiente utilizado:** Microsoft Windows 11 Pro (`10.0.26300`), AMD Ryzen 7 5800X3D (8-Core), 31,92 GB RAM, Python `3.12.7` (`win32`), `pandas==3.0.3`, `pytest==9.0.2` (`.venv` isolada).
- **Natureza dos dados:** 100% sintéticos, gerados em pasta temporária por `scripts/benchmark_volumes.py` e removidos automaticamente após a medição.
- **Objetivo:** observar o comportamento funcional e o tempo efetivamente medido da implementação em Python + Pandas + `Decimal` em diferentes volumes — **sem** alegar desempenho industrial nem substituir testes de carga de produção.

## Resultados Efetivamente Medidos

| Volume (linhas) | Válidos | Rejeitados (~5%) | Faturamento Total | Reconciliação | Processamento (s) | Total com Exportação (s) |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 1.000 | 950 | 50 | R$ 2.956.224,00 | APROVADA (11/11) | 0.0734 | 0.1141 |
| 10.000 | 9.500 | 500 | R$ 29.562.240,00 | APROVADA (11/11) | 0.2116 | 0.3214 |
| 100.000 | 95.000 | 5.000 | R$ 295.622.400,00 | APROVADA (11/11) | 1.6686 | 2.8463 |

## Observações Técnicas

- Todos os 3 volumes mantiveram reconciliação matemática `11/11` com diferença monetária exata `0,00` em `Decimal`.
- Os arquivos temporários de volume foram excluídos ao final da execução para manter o repositório e o pacote ZIP enxutos.
- O tempo de execução varia conforme hardware, carga do sistema operacional e disco local.
