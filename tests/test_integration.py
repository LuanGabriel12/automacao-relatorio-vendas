"""Testes de integração ponta a ponta, paridade V1, cenários, idempotência e conformidade."""

from decimal import Decimal
import json
from pathlib import Path

import pytest

from src.config import (
    ARQUIVOS_SAIDA,
    PASTA_DADOS_ENTRADA,
    PASTA_EXEMPLOS,
    RAIZ_PROJETO,
    STATUS_CONCLUIDO_PARCIALMENTE,
    STATUS_SEM_VENDAS_VALIDAS,
    STATUS_SUCESSO,
)
from src.pipeline import executar_pipeline
import src.reporting.exports as modulo_exports


def test_fluxo_completo_dados_originais_reproduz_v1_sem_ruido_float(tmp_path):
    res = executar_pipeline(
        pasta_entrada=PASTA_DADOS_ENTRADA,
        pasta_saida=tmp_path,
        salvar_arquivos=True,
    )

    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["reconciliacao"]["aprovada"] is True
    assert res["reconciliacao"]["total_aprovadas"] == 11

    # Paridade histórica exata com a V1
    assert res["kpis"]["total_registros_recebidos"] == 42
    assert res["kpis"]["registros_validos"] == 36
    assert res["kpis"]["registros_rejeitados"] == 6
    assert res["kpis"]["quantidade_pedidos"] == 36
    assert res["kpis"]["unidades_vendidas"] == 120
    assert res["kpis"]["faturamento_total"] == Decimal("65068.00")
    assert res["resumo_execucao"]["kpis"]["ticket_medio_pedido"] == "1807.44"

    # Verifica que todos os 11 arquivos esperados foram gerados com LF
    for nome in ARQUIVOS_SAIDA.values():
        caminho = tmp_path / nome
        assert caminho.exists(), f"Arquivo ausente: {nome}"
        assert b"\r\n" not in caminho.read_bytes(), f"CRLF encontrado em {nome}"

    # Verifica ausência de artefato float (ex.: 269,70000000000005 da V1)
    texto_vendas = (tmp_path / "vendas_tratadas.csv").read_text(encoding="utf-8")
    assert "0000000" not in texto_vendas
    assert "269,70" in texto_vendas

    resumo_lido = json.loads((tmp_path / "resumo_execucao.json").read_text(encoding="utf-8"))
    assert resumo_lido["status_execucao"] == STATUS_SUCESSO
    assert resumo_lido["flags"]["todos_arquivos_aceitos"] is True


def test_reexecucao_mesmos_dados_e_idempotente(tmp_path):
    res1 = executar_pipeline(PASTA_DADOS_ENTRADA, tmp_path, salvar_arquivos=True)
    vendas_1 = (tmp_path / "vendas_tratadas.csv").read_text(encoding="utf-8")
    incons_1 = (tmp_path / "inconsistencias.csv").read_text(encoding="utf-8")
    kpis_1 = (tmp_path / "kpis_executivos.csv").read_text(encoding="utf-8")

    res2 = executar_pipeline(PASTA_DADOS_ENTRADA, tmp_path, salvar_arquivos=True)
    vendas_2 = (tmp_path / "vendas_tratadas.csv").read_text(encoding="utf-8")
    incons_2 = (tmp_path / "inconsistencias.csv").read_text(encoding="utf-8")
    kpis_2 = (tmp_path / "kpis_executivos.csv").read_text(encoding="utf-8")

    assert res1["kpis"]["faturamento_total"] == res2["kpis"]["faturamento_total"]
    assert res1["kpis"]["registros_validos"] == res2["kpis"]["registros_validos"]
    assert vendas_1 == vendas_2
    assert incons_1 == incons_2
    assert kpis_1 == kpis_2


def test_falha_bloqueante_nao_sobrescreve_relatorios_validos_anteriores(tmp_path):
    pasta_saida = tmp_path / "saida"
    executar_pipeline(PASTA_DADOS_ENTRADA, pasta_saida, salvar_arquivos=True)
    conteudo_valido_antes = (pasta_saida / "kpis_executivos.csv").read_text(encoding="utf-8")

    # Pasta com apenas um arquivo vazio -> erro bloqueante (0 arquivos aceitos)
    pasta_invalida = tmp_path / "entrada_invalida"
    pasta_invalida.mkdir()
    (pasta_invalida / "vazio.csv").write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        executar_pipeline(pasta_invalida, pasta_saida, salvar_arquivos=True)

    conteudo_valido_depois = (pasta_saida / "kpis_executivos.csv").read_text(encoding="utf-8")
    assert conteudo_valido_depois == conteudo_valido_antes


def test_cenario_sintetico_valido(tmp_path):
    res = executar_pipeline(PASTA_EXEMPLOS / "cenario_valido", tmp_path, salvar_arquivos=True)
    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["kpis"]["registros_validos"] == 3
    assert res["kpis"]["registros_rejeitados"] == 0
    assert res["kpis"]["faturamento_total"] == Decimal("5700.00")


def test_cenario_sintetico_registros_invalidos(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_registros_invalidos", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["kpis"]["total_registros_recebidos"] == 6
    assert res["kpis"]["registros_validos"] == 1
    assert res["kpis"]["registros_rejeitados"] == 5
    assert res["validacao"]["total_linhas_multiplos_erros"] >= 2
    assert res["kpis"]["faturamento_total"] == Decimal("180.00")


def test_cenario_sintetico_duplicatas(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_duplicatas", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["kpis"]["registros_validos"] == 3
    assert res["kpis"]["registros_rejeitados"] == 2
    assert res["kpis"]["faturamento_total"] == Decimal("1700.00")


def test_cenario_sintetico_multiplos_itens_e_alerta_investigacao(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_multiplos_itens", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["kpis"]["registros_validos"] == 5
    assert res["kpis"]["quantidade_pedidos"] == 2
    assert res["kpis"]["faturamento_total"] == Decimal("4650.00")
    assert res["kpis"]["ticket_medio_pedido"] == Decimal("2325.00")
    assert len(res["validacao"]["alertas_investigacao"]) == 1


def test_cenario_sintetico_arquivo_vazio_marca_concluido_parcialmente(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_arquivo_vazio", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_CONCLUIDO_PARCIALMENTE
    assert res["status_execucao"] != STATUS_SUCESSO
    assert len(res["ingestao"]["arquivos_aceitos"]) == 1
    assert len(res["ingestao"]["arquivos_rejeitados"]) == 2
    assert res["resumo_execucao"]["flags"]["todos_arquivos_aceitos"] is False


def test_cenario_sintetico_sem_colunas_obrigatorias_marca_parcial(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_sem_colunas_obrigatorias", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_CONCLUIDO_PARCIALMENTE
    assert len(res["ingestao"]["arquivos_rejeitados"]) == 1


def test_cenario_sintetico_sem_vendas_validas(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_sem_vendas_validas", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_SEM_VENDAS_VALIDAS
    assert res["kpis"]["registros_validos"] == 0
    assert res["kpis"]["registros_rejeitados"] == 3
    assert res["kpis"]["faturamento_total"] == Decimal("0.00")
    assert res["reconciliacao"]["aprovada"] is True


def test_cenario_sintetico_conflito_entre_arquivos(tmp_path):
    res = executar_pipeline(
        PASTA_EXEMPLOS / "cenario_conflito_entre_arquivos", tmp_path, salvar_arquivos=True
    )
    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["kpis"]["registros_validos"] == 1
    assert res["kpis"]["registros_rejeitados"] == 4
    assert res["kpis"]["faturamento_total"] == Decimal("200.00")
    assert res["validacao"]["pedidos_conflito_data"] == ["S-8001"]
    assert res["validacao"]["pedidos_conflito_loja"] == ["S-8002"]


def test_csvs_originais_preservados_em_lf():
    for nome in ["vendas_janeiro.csv", "vendas_fevereiro.csv", "vendas_marco.csv"]:
        caminho = PASTA_DADOS_ENTRADA / nome
        assert caminho.exists()
        assert b"\r\n" not in caminho.read_bytes(), f"CRLF inesperado em {nome}"


def test_ausencia_de_importacoes_diretas_de_bibliotecas_proibidas():
    proibidas = [
        "import numpy",
        "from numpy",
        "import matplotlib",
        "from matplotlib",
        "import seaborn",
        "from seaborn",
        "import polars",
        "from polars",
        "import pyspark",
        "from pyspark",
        "import airflow",
        "from airflow",
        "import celery",
        "from celery",
    ]
    arquivos_v2 = [RAIZ_PROJETO / "main.py"]
    arquivos_v2.extend(sorted((RAIZ_PROJETO / "src").rglob("*.py")))
    arquivos_v2.extend(sorted((RAIZ_PROJETO / "tests").rglob("*.py")))
    arquivos_v2.extend(sorted((RAIZ_PROJETO / "scripts").rglob("*.py")))

    for arquivo in arquivos_v2:
        conteudo = arquivo.read_text(encoding="utf-8")
        for linha in conteudo.splitlines():
            linha_limpa = linha.strip()
            if linha_limpa.startswith("#"):
                continue
            for proibida in proibidas:
                assert not linha_limpa.startswith(proibida), (
                    f"Importação proibida '{proibida}' encontrada em {arquivo.name}"
                )


def test_falha_durante_exportacao_executa_rollback_e_preserva_lote_anterior(tmp_path):
    """Regressão: falha na 2ª gravação não pode misturar arquivos da execução 1 e 2."""
    pasta_saida = tmp_path / "saida"
    executar_pipeline(PASTA_DADOS_ENTRADA, pasta_saida, salvar_arquivos=True)

    snapshot_antes = {
        nome: (pasta_saida / nome).read_bytes() for nome in ARQUIVOS_SAIDA.values()
    }

    escrita_original = modulo_exports._escrever_texto_atomico
    contador = {"chamadas": 0}

    def falha_na_segunda_chamada(caminho_final, conteudo):
        contador["chamadas"] += 1
        if contador["chamadas"] == 2:
            raise OSError("Falha simulada na segunda gravação")
        return escrita_original(caminho_final, conteudo)

    modulo_exports._escrever_texto_atomico = falha_na_segunda_chamada
    try:
        with pytest.raises(RuntimeError):
            executar_pipeline(
                PASTA_EXEMPLOS / "cenario_valido", pasta_saida, salvar_arquivos=True
            )
    finally:
        modulo_exports._escrever_texto_atomico = escrita_original

    # Todos os 11 arquivos devem permanecer exatamente iguais ao lote anterior
    for nome, bytes_esperados in snapshot_antes.items():
        assert (pasta_saida / nome).read_bytes() == bytes_esperados

    # Nenhum arquivo .tmp residual deve sobrar
    assert list(pasta_saida.glob("*.tmp")) == []


def test_falha_durante_exportacao_em_pasta_vazia_nao_deixa_lote_incompleto(tmp_path):
    """Regressão: falha no meio da primeira exportação limpa arquivos já gravados."""
    pasta_saida = tmp_path / "saida_vazia"

    escrita_original = modulo_exports._escrever_texto_atomico
    contador = {"chamadas": 0}

    def falha_na_segunda_chamada(caminho_final, conteudo):
        contador["chamadas"] += 1
        if contador["chamadas"] == 2:
            raise OSError("Falha simulada na segunda gravação")
        return escrita_original(caminho_final, conteudo)

    modulo_exports._escrever_texto_atomico = falha_na_segunda_chamada
    try:
        with pytest.raises(RuntimeError):
            executar_pipeline(
                PASTA_EXEMPLOS / "cenario_valido", pasta_saida, salvar_arquivos=True
            )
    finally:
        modulo_exports._escrever_texto_atomico = escrita_original

    assert list(pasta_saida.iterdir()) == []


def test_fluxo_completo_preserva_quantidade_inteira_acima_limite_float64(
    criar_csv, tmp_path
):
    """Regressão ponta a ponta: 9007199254740993 + linha inválida mantém precisão exata."""
    pasta_in = tmp_path / "entrada"
    pasta_out = tmp_path / "saida"
    criar_csv(
        "vendas_extremo.csv",
        [
            "05/01/2026;P-EXT;Centro;Mouse;Acessórios;9007199254740993;10,00",
            "06/01/2026;P-INV;Centro;Mouse;Acessórios;abc;10,00",
        ],
        pasta=pasta_in,
    )

    res = executar_pipeline(pasta_in, pasta_out, salvar_arquivos=True)

    assert res["status_execucao"] == STATUS_SUCESSO
    assert res["reconciliacao"]["aprovada"] is True
    assert res["kpis"]["unidades_vendidas"] == 9007199254740993
    assert res["kpis"]["faturamento_total"] == Decimal("90071992547409930.00")
    assert res["analises"]["lojas"].loc[0, "Quantidade"] == 9007199254740993

    csv_tratadas = (pasta_out / "vendas_tratadas.csv").read_text(encoding="utf-8")
    assert ";9007199254740993;10,00;90071992547409930,00;" in csv_tratadas
