"""Ponto de entrada principal do Sales Automation Engine V2."""

import sys

from src.config import (
    PASTA_DADOS_ENTRADA,
    PASTA_RESULTADO,
    STATUS_CONCLUIDO_PARCIALMENTE,
    STATUS_PARCIAL_SEM_VENDAS_VALIDAS,
    STATUS_SEM_VENDAS_VALIDAS,
    STATUS_SUCESSO,
)
from src.pipeline import executar_pipeline
from src.reporting.exports import (
    formatar_moeda_br,
    formatar_numero_br,
    formatar_percentual_br,
)


def exibir_resumo_terminal(resultado):
    """Exibe resumo operacional claro e honesto da execução no terminal."""
    status = resultado["status_execucao"]
    ingestao = resultado["ingestao"]
    validacao = resultado["validacao"]
    kpis = resultado["kpis"]
    reconciliacao = resultado["reconciliacao"]

    print("=" * 68)
    print("SALES AUTOMATION ENGINE V2 — RESUMO DA EXECUÇÃO")
    print("=" * 68)
    print(f"Data/hora:              {resultado['timestamp_execucao']}")
    print(f"Status da execução:     {status}")

    if status == STATUS_SUCESSO:
        print("Resultado:              Processamento integral concluído e reconciliado.")
    elif status in (STATUS_CONCLUIDO_PARCIALMENTE, STATUS_PARCIAL_SEM_VENDAS_VALIDAS):
        print(
            "ATENÇÃO (PARCIAL):      Existem arquivos rejeitados integralmente! "
            "Esta execução NÃO foi integralmente bem-sucedida."
        )
    elif status == STATUS_SEM_VENDAS_VALIDAS:
        print("ATENÇÃO:                Nenhuma venda válida restou após a validação.")

    print("-" * 68)
    print(
        f"Arquivos encontrados:   {ingestao['total_arquivos_encontrados']} "
        f"(aceitos: {len(ingestao['arquivos_aceitos'])} | "
        f"rejeitados: {len(ingestao['arquivos_rejeitados'])})"
    )
    if len(ingestao["arquivos_rejeitados"]) > 0:
        for item in ingestao["arquivos_rejeitados"]:
            print(f"  - Rejeitado: {item['arquivo']} -> {item['motivo']}")

    print("-" * 68)
    print(
        f"Registros recebidos:    {formatar_numero_br(kpis['total_registros_recebidos'], 0)} "
        "(apenas arquivos aceitos)"
    )
    print(f"Vendas válidas:         {formatar_numero_br(kpis['registros_validos'], 0)}")
    print(
        f"Inconsistências:        {formatar_numero_br(kpis['registros_rejeitados'], 0)} "
        f"({formatar_percentual_br(kpis['taxa_rejeicao_pct'])})"
    )
    print(f"Pedidos distintos:      {formatar_numero_br(kpis['quantidade_pedidos'], 0)}")
    print(f"Unidades vendidas:      {formatar_numero_br(kpis['unidades_vendidas'], 0)}")
    print(f"Faturamento total:      {formatar_moeda_br(kpis['faturamento_total'])}")
    print(f"Ticket médio/pedido:    {formatar_moeda_br(kpis['ticket_medio_pedido'])}")
    print(f"Receita por unidade:    {formatar_moeda_br(kpis['receita_por_unidade'])}")
    print("-" * 68)
    print(
        f"Reconciliação:          "
        f"{'APROVADA' if reconciliacao['aprovada'] else 'REPROVADA'} "
        f"({reconciliacao['total_aprovadas']}/{reconciliacao['total_verificacoes']} verificações)"
    )
    print(
        f"Alertas investigação:   {len(validacao['alertas_investigacao'])} "
        "(Pedido + Produto recorrente)"
    )
    print(f"Tempo de execução:      {resultado['duracao_segundos']:.4f} s")
    print(f"Pasta de saída:         {PASTA_RESULTADO}")
    print(f"Arquivos gerados:       {len(resultado['caminhos_salvos'])}")
    print("=" * 68)


def main():
    """Coordena a execução padrão do pipeline via linha de comando."""
    try:
        resultado = executar_pipeline(
            pasta_entrada=PASTA_DADOS_ENTRADA,
            pasta_saida=PASTA_RESULTADO,
            salvar_arquivos=True,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as erro:
        print("=" * 68)
        print("SALES AUTOMATION ENGINE V2 — FALHA NA EXECUÇÃO")
        print("=" * 68)
        print(f"Motivo: {erro}")
        print(
            "Proteção de saída: nenhum relatório válido anterior foi sobrescrito."
        )
        print("=" * 68)
        sys.exit(1)

    exibir_resumo_terminal(resultado)


if __name__ == "__main__":
    main()
