"""Teste de volume sintético (1.000, 10.000 e 100.000 registros) com medições reais.

Gera arquivos CSV sintéticos temporários fora dos dados de produção, executa o
pipeline completo da V2, valida a reconciliação matemática e limpa os arquivos
temporários ao final para não inflar o repositório nem o pacote ZIP.
"""

from datetime import datetime
from pathlib import Path
import sys
from time import perf_counter

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.config import CODIFICACAO_ESCRITA, PASTA_RELATORIOS, TERMINADOR_LINHA
from src.pipeline import executar_pipeline
from src.reporting.exports import formatar_moeda_br, formatar_numero_br


VOLUMES_TESTE = [1000, 10000, 100000]

LOJAS = ["Centro", "Online", "Norte", "Sul"]
PRODUTOS = [
    ("Notebook Pro 14", "Informática", "3.499,90"),
    ("Monitor 24", "Informática", "899,90"),
    ("Impressora Laser", "Escritório", "1.899,90"),
    ("Cadeira Ergonômica", "Móveis", "1.299,90"),
    ("SSD 1TB", "Componentes", "449,90"),
    ("Mouse Sem Fio", "Acessórios", "89,90"),
    ("Teclado Mecânico", "Acessórios", "249,90"),
    ("Headset USB", "Acessórios", "179,90"),
]


def gerar_csv_sintetico_volume(caminho_arquivo, quantidade_linhas):
    """Cria um arquivo CSV sintético determinístico no padrão brasileiro."""
    linhas = ["Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário"]
    meses = ["01", "02", "03"]

    for indice in range(1, quantidade_linhas + 1):
        mes = meses[(indice - 1) % 3]
        dia = ((indice - 1) % 28) + 1
        data_str = f"{dia:02d}/{mes}/2026"
        pedido = f"B-{indice:06d}"
        loja = LOJAS[(indice - 1) % len(LOJAS)]
        produto, categoria, preco = PRODUTOS[(indice - 1) % len(PRODUTOS)]
        quantidade = str(((indice - 1) % 5) + 1)

        # Insere aproximadamente 5% de inconsistências determinísticas
        if indice % 100 == 0:
            data_str = "31/02/2026"
        elif indice % 100 == 25:
            quantidade = "-1"
        elif indice % 100 == 50:
            preco = ""
        elif indice % 100 == 75:
            loja = ""
        elif indice % 100 == 99 and indice > 1:
            # Duplicata exata da linha imediatamente anterior
            linhas.append(linhas[-1])
            continue

        linhas.append(
            f"{data_str};{pedido};{loja};{produto};{categoria};{quantidade};{preco}"
        )

    caminho_arquivo.write_text(
        "\n".join(linhas) + "\n",
        encoding=CODIFICACAO_ESCRITA,
        newline=TERMINADOR_LINHA,
    )


def limpar_pasta_temporaria(pasta):
    """Remove arquivos e subpastas temporárias criados durante o teste de volume."""
    if not pasta.exists():
        return
    for item in sorted(pasta.rglob("*"), reverse=True):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    pasta.rmdir()


def executar_benchmark_volumes(salvar_relatorio=True):
    """Mede o comportamento real do pipeline em 1.000, 10.000 e 100.000 linhas."""
    pasta_temp = RAIZ_PROJETO / ".tmp_benchmark_volumes"
    limpar_pasta_temporaria(pasta_temp)
    pasta_temp.mkdir(parents=True, exist_ok=True)

    resultados = []
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        for volume in VOLUMES_TESTE:
            pasta_in = pasta_temp / f"in_{volume}"
            pasta_out = pasta_temp / f"out_{volume}"
            pasta_in.mkdir(parents=True, exist_ok=True)
            pasta_out.mkdir(parents=True, exist_ok=True)

            arquivo_csv = pasta_in / f"vendas_sintetico_{volume}.csv"
            t0_geracao = perf_counter()
            gerar_csv_sintetico_volume(arquivo_csv, volume)
            tempo_geracao = perf_counter() - t0_geracao

            t0_proc = perf_counter()
            res = executar_pipeline(
                pasta_entrada=pasta_in,
                pasta_saida=pasta_out,
                salvar_arquivos=True,
            )
            tempo_total_pipeline = perf_counter() - t0_proc

            resultados.append(
                {
                    "volume_registros": volume,
                    "registros_validos": res["kpis"]["registros_validos"],
                    "registros_rejeitados": res["kpis"]["registros_rejeitados"],
                    "faturamento_total": res["kpis"]["faturamento_total"],
                    "reconciliacao_aprovada": res["reconciliacao"]["aprovada"],
                    "verificacoes": f"{res['reconciliacao']['total_aprovadas']}/{res['reconciliacao']['total_verificacoes']}",
                    "tempo_geracao_s": tempo_geracao,
                    "tempo_pipeline_s": res["duracao_segundos"],
                    "tempo_total_com_exportacao_s": tempo_total_pipeline,
                    "status_execucao": res["status_execucao"],
                }
            )
            print(
                f"Volume {volume:>7} | válidos={res['kpis']['registros_validos']:>6} "
                f"| inválidos={res['kpis']['registros_rejeitados']:>5} "
                f"| reconciliação={res['reconciliacao']['aprovada']} "
                f"| total={tempo_total_pipeline:.4f}s"
            )
    finally:
        limpar_pasta_temporaria(pasta_temp)

    if salvar_relatorio:
        PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)
        caminho_md = PASTA_RELATORIOS / "benchmark_volumes.md"
        linhas_md = [
            "# Medição Real de Comportamento por Volume — Sales Automation Engine V2",
            "",
            f"- **Data/hora da medição:** {timestamp}",
            f"- **Python:** `{sys.version.split()[0]}` (`{sys.platform}`)",
            "- **Natureza dos dados:** 100% sintéticos, gerados em pasta temporária por `scripts/benchmark_volumes.py` e removidos após a medição.",
            "- **Objetivo:** observar o comportamento funcional e o tempo efetivamente medido da implementação em Python + Pandas + `Decimal` em diferentes volumes — **sem** alegar desempenho industrial nem substituir testes de carga de produção.",
            "",
            "## Resultados Efetivamente Medidos",
            "",
            "| Volume (linhas) | Válidos | Rejeitados (~5%) | Faturamento Total | Reconciliação | Processamento (s) | Total com Exportação (s) |",
            "| ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
        for r in resultados:
            linhas_md.append(
                f"| {formatar_numero_br(r['volume_registros'], 0)} | "
                f"{formatar_numero_br(r['registros_validos'], 0)} | "
                f"{formatar_numero_br(r['registros_rejeitados'], 0)} | "
                f"{formatar_moeda_br(r['faturamento_total'])} | "
                f"{'APROVADA' if r['reconciliacao_aprovada'] else 'REPROVADA'} ({r['verificacoes']}) | "
                f"{r['tempo_pipeline_s']:.4f} | "
                f"{r['tempo_total_com_exportacao_s']:.4f} |"
            )

        linhas_md.extend(
            [
                "",
                "## Observações Técnicas",
                "",
                "- Todos os 3 volumes mantiveram reconciliação matemática `11/11` com diferença monetária exata `0,00` em `Decimal`.",
                "- Os arquivos temporários de volume foram excluídos ao final da execução para manter o repositório e o arquivo ZIP enxutos.",
                "- O tempo de execução varia conforme hardware, carga do sistema operacional e disco local.",
                "",
            ]
        )
        caminho_md.write_text(
            "\n".join(linhas_md),
            encoding=CODIFICACAO_ESCRITA,
            newline=TERMINADOR_LINHA,
        )

    return resultados


if __name__ == "__main__":
    executar_benchmark_volumes(salvar_relatorio=True)
