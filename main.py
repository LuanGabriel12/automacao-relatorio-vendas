"""Executa a automação do relatório de vendas."""

import argparse
from pathlib import Path

from src.relatorio_vendas import executar_pipeline


PASTA_PROJETO = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        description="Consolida arquivos de vendas e gera um relatório Excel."
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=PASTA_PROJETO / "dados" / "entrada",
        help="Pasta com os arquivos CSV ou XLSX.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=PASTA_PROJETO / "resultado" / "relatorio_vendas.xlsx",
        help="Local onde o relatório será salvo.",
    )
    argumentos = parser.parse_args()

    caminho_log = PASTA_PROJETO / "logs" / "execucao.log"

    try:
        resultado = executar_pipeline(
            argumentos.entrada,
            argumentos.saida,
            caminho_log,
        )
    except (FileNotFoundError, PermissionError, ValueError) as erro:
        print(f"Erro: {erro}")
        raise SystemExit(1) from erro

    print("Relatório gerado com sucesso.")
    print(f"Vendas válidas: {resultado['registros_validos']}")
    print(f"Registros descartados: {resultado['registros_descartados']}")
    print(f"Duplicados removidos: {resultado['duplicados_removidos']}")
    print(f"Arquivo: {resultado['arquivo_saida']}")


if __name__ == "__main__":
    main()
