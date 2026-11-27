"""Orquestração completa do pipeline de processamento comercial V2."""

from datetime import datetime
from time import perf_counter

from src.analytics.commercial_analysis import gerar_analises_comerciais
from src.analytics.kpis import (
    calcular_kpis_executivos,
    construir_tabela_kpis_executivos,
)
from src.config import (
    PASTA_DADOS_ENTRADA,
    PASTA_RESULTADO,
    STATUS_CONCLUIDO_PARCIALMENTE,
    STATUS_FALHA,
    STATUS_PARCIAL_SEM_VENDAS_VALIDAS,
    STATUS_SEM_VENDAS_VALIDAS,
    STATUS_SUCESSO,
)
from src.data.cleaning import separar_vendas_e_inconsistencias
from src.data.loader import carregar_arquivos_entrada
from src.data.validation import validar_vendas
from src.reporting.exports import exportar_resultados, gerar_resumo_execucao_dict
from src.reporting.reconciliation import executar_reconciliacao


def determinar_status_execucao(
    quantidade_arquivos_rejeitados,
    total_registros_validos,
    reconciliacao_aprovada,
):
    """Define o status explícito da execução sem mascarar execuções parciais."""
    if not reconciliacao_aprovada:
        return STATUS_FALHA

    houve_arquivos_rejeitados = quantidade_arquivos_rejeitados > 0
    if houve_arquivos_rejeitados and total_registros_validos == 0:
        return STATUS_PARCIAL_SEM_VENDAS_VALIDAS
    if houve_arquivos_rejeitados:
        return STATUS_CONCLUIDO_PARCIALMENTE
    if total_registros_validos == 0:
        return STATUS_SEM_VENDAS_VALIDAS
    return STATUS_SUCESSO


def executar_pipeline(
    pasta_entrada=PASTA_DADOS_ENTRADA,
    pasta_saida=PASTA_RESULTADO,
    salvar_arquivos=True,
):
    """Executa todas as etapas do Sales Automation Engine V2 ponta a ponta.

    Política de erros:
    - Pasta inexistente ou sem arquivos CSV: levanta ``FileNotFoundError`` (não altera saída).
    - Todos os arquivos rejeitados estruturalmente: levanta ``ValueError`` (não altera saída).
    - Reconciliação matemática reprovada: levanta ``RuntimeError`` (não altera saída).
    - Arquivos parcialmente rejeitados: processa arquivos aceitos, reconcilia e
      sinaliza ``CONCLUIDO_PARCIALMENTE`` (nunca ``SUCESSO`` integral).
    """
    inicio = perf_counter()
    timestamp_execucao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # 1. Ingestão dinâmica
    resultado_ingestao = carregar_arquivos_entrada(pasta_entrada)

    if len(resultado_ingestao["arquivos_aceitos"]) == 0:
        detalhes = "; ".join(
            f"{item['arquivo']} ({item['motivo']})"
            for item in resultado_ingestao["arquivos_rejeitados"]
        )
        raise ValueError(
            "Nenhum arquivo CSV válido pôde ser processado. "
            f"Arquivos rejeitados: {detalhes}"
        )

    # 2. Validação de qualidade dos dados
    resultado_validacao = validar_vendas(resultado_ingestao["dados_brutos"])

    # 3. Limpeza, normalização e separação
    vendas_validas, inconsistencias = separar_vendas_e_inconsistencias(
        resultado_validacao["dados_validados"]
    )

    # 4. Indicadores executivos e inteligência comercial
    kpis = calcular_kpis_executivos(
        vendas_validas=vendas_validas,
        total_registros_recebidos=resultado_validacao["total_registros_recebidos"],
        total_registros_rejeitados=resultado_validacao["total_registros_rejeitados"],
    )
    tabela_kpis = construir_tabela_kpis_executivos(kpis)
    analises = gerar_analises_comerciais(vendas_validas)

    # 5. Reconciliação matemática obrigatória (antes de tocar na pasta de saída)
    resultado_reconciliacao = executar_reconciliacao(
        resultado_ingestao=resultado_ingestao,
        vendas_validas=vendas_validas,
        inconsistencias=inconsistencias,
        kpis=kpis,
        analises=analises,
    )

    if not resultado_reconciliacao["aprovada"]:
        codigos_falha = [
            item["codigo"]
            for item in resultado_reconciliacao["verificacoes"]
            if not item["aprovada"]
        ]
        raise RuntimeError(
            "Falha na reconciliação matemática. Relatórios anteriores foram "
            f"preservados. Verificações reprovadas: {', '.join(codigos_falha)}"
        )

    status_execucao = determinar_status_execucao(
        quantidade_arquivos_rejeitados=len(resultado_ingestao["arquivos_rejeitados"]),
        total_registros_validos=resultado_validacao["total_registros_validos"],
        reconciliacao_aprovada=resultado_reconciliacao["aprovada"],
    )

    duracao_segundos = perf_counter() - inicio

    # 6. Exportação segura e atômica
    caminhos_salvos = []
    if salvar_arquivos:
        caminhos_salvos, resumo_execucao = exportar_resultados(
            pasta_saida=pasta_saida,
            timestamp_execucao=timestamp_execucao,
            duracao_segundos=duracao_segundos,
            status_execucao=status_execucao,
            resultado_ingestao=resultado_ingestao,
            resultado_validacao=resultado_validacao,
            vendas_validas=vendas_validas,
            inconsistencias=inconsistencias,
            kpis=kpis,
            tabela_kpis=tabela_kpis,
            analises=analises,
            resultado_reconciliacao=resultado_reconciliacao,
        )
    else:
        resumo_execucao = gerar_resumo_execucao_dict(
            timestamp_execucao=timestamp_execucao,
            duracao_segundos=duracao_segundos,
            status_execucao=status_execucao,
            resultado_ingestao=resultado_ingestao,
            resultado_validacao=resultado_validacao,
            kpis=kpis,
            resultado_reconciliacao=resultado_reconciliacao,
            arquivos_gerados=[],
        )

    return {
        "status_execucao": status_execucao,
        "timestamp_execucao": timestamp_execucao,
        "duracao_segundos": duracao_segundos,
        "ingestao": resultado_ingestao,
        "validacao": resultado_validacao,
        "vendas_validas": vendas_validas,
        "inconsistencias": inconsistencias,
        "kpis": kpis,
        "tabela_kpis": tabela_kpis,
        "analises": analises,
        "reconciliacao": resultado_reconciliacao,
        "resumo_execucao": resumo_execucao,
        "caminhos_salvos": caminhos_salvos,
    }
