"""Testes automatizados da camada de ingestão (src/data/loader.py)."""

import pytest

from src.data.loader import (
    carregar_arquivos_entrada,
    ler_arquivo_csv_individual,
    listar_arquivos_csv,
)


def test_listar_arquivos_csv_em_ordem_deterministica(criar_csv, tmp_path):
    criar_csv("b_vendas.csv", ["05/01/2026;P-1;Centro;Mouse;Acessórios;1;50,00"])
    criar_csv("a_vendas.csv", ["06/01/2026;P-2;Sul;Teclado;Acessórios;2;100,00"])
    (tmp_path / "ignorar.txt").write_text("nao e csv", encoding="utf-8")

    arquivos = listar_arquivos_csv(tmp_path)
    assert [a.name for a in arquivos] == ["a_vendas.csv", "b_vendas.csv"]


def test_pasta_inexistente_levanta_file_not_found(tmp_path):
    pasta_inexistente = tmp_path / "nao_existe"
    with pytest.raises(FileNotFoundError):
        carregar_arquivos_entrada(pasta_inexistente)


def test_pasta_sem_csv_levanta_file_not_found(tmp_path):
    (tmp_path / "notas.txt").write_text("texto", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        carregar_arquivos_entrada(tmp_path)


def test_carregar_multiplos_csvs_preserva_texto_bruto_e_origem(criar_csv, tmp_path):
    criar_csv(
        "mes1.csv",
        [
            "05/01/2026;P-1;Centro;Notebook;Informática;1;3.499,90",
            "31/02/2026;P-2;Sul;Mouse;Acessórios;abc;inf",
        ],
    )
    criar_csv(
        "mes2.csv",
        ["10/02/2026;P-3;Online;Monitor;Informática;2;899,90"],
    )

    resultado = carregar_arquivos_entrada(tmp_path)
    df = resultado["dados_brutos"]

    assert resultado["total_arquivos_encontrados"] == 2
    assert len(resultado["arquivos_aceitos"]) == 2
    assert len(resultado["arquivos_rejeitados"]) == 0
    assert resultado["total_registros_recebidos"] == 3
    assert list(df["Arquivo de origem"]) == ["mes1.csv", "mes1.csv", "mes2.csv"]
    assert list(df["Linha no arquivo"]) == [2, 3, 2]
    # Valores brutos inválidos preservados sem alteração silenciosa
    assert df.loc[1, "Quantidade"] == "abc"
    assert df.loc[1, "Preço Unitário"] == "inf"
    assert df.loc[1, "Data"] == "31/02/2026"


def test_arquivo_vazio_zero_bytes_e_apenas_cabecalho_sao_rejeitados(criar_csv, tmp_path):
    criar_csv("valido.csv", ["05/01/2026;P-1;Centro;Mouse;Acessórios;1;50,00"])
    (tmp_path / "zero_bytes.csv").write_text("", encoding="utf-8")
    criar_csv("somente_cabecalho.csv", [])

    resultado = carregar_arquivos_entrada(tmp_path)

    assert len(resultado["arquivos_aceitos"]) == 1
    assert resultado["arquivos_aceitos"][0]["arquivo"] == "valido.csv"
    assert len(resultado["arquivos_rejeitados"]) == 2
    rejeitados = {item["arquivo"]: item["motivo"] for item in resultado["arquivos_rejeitados"]}
    assert "vazio" in rejeitados["zero_bytes.csv"].lower()
    assert "apenas cabeçalho" in rejeitados["somente_cabecalho.csv"].lower()
    assert resultado["total_registros_recebidos"] == 1


def test_arquivo_sem_colunas_obrigatorias_e_rejeitado(criar_csv, tmp_path):
    criar_csv("ok.csv", ["05/01/2026;P-1;Centro;Mouse;Acessórios;1;50,00"])
    criar_csv(
        "incompleto.csv",
        ["Data;Pedido;Loja", "05/01/2026;P-2;Sul"],
        incluir_cabecalho=False,
    )

    resultado = carregar_arquivos_entrada(tmp_path)

    assert len(resultado["arquivos_aceitos"]) == 1
    assert len(resultado["arquivos_rejeitados"]) == 1
    motivo = resultado["arquivos_rejeitados"][0]["motivo"]
    assert "Colunas obrigatórias ausentes" in motivo
    assert "Preço Unitário" in motivo


def test_arquivo_com_codificacao_invalida_e_rejeitado(tmp_path):
    caminho = tmp_path / "latin1_invalido.csv"
    caminho.write_bytes(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário\n"
        "05/01/2026;P-1;Centro;Teclado Mecânico;Acessórios;1;100,00\n".encode("latin-1")
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert resultado is None
    assert "codificação" in motivo.lower()


def test_arquivo_utf8_com_bom_e_lido_sem_corromper_cabecalho(criar_csv, tmp_path):
    caminho = criar_csv(
        "com_bom.csv",
        ["05/01/2026;P-1;Centro;Mouse;Acessórios;2;89,90"],
        encoding="utf-8-sig",
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert motivo is None
    df, metadados = resultado
    assert "Data" in df.columns
    assert metadados["registros_lidos"] == 1


def test_arquivo_com_colunas_extras_registra_colunas_ignoradas(criar_csv, tmp_path):
    caminho = criar_csv(
        "com_extra.csv",
        [
            "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário;Observacao",
            "05/01/2026;P-1;Centro;Mouse;Acessórios;2;89,90;promo",
        ],
        incluir_cabecalho=False,
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert motivo is None
    df, metadados = resultado
    assert metadados["colunas_extras_ignoradas"] == ["Observacao"]
    assert "Observacao" not in df.columns


def test_arquivo_csv_com_colunas_sobrando_na_primeira_linha_e_rejeitado(tmp_path):
    caminho = tmp_path / "colunas_sobrando.csv"
    caminho.write_text(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário\n"
        "05/01/2026;P-1;Centro;Mouse;Acessórios;2;89,90;coluna_sobrando_1;coluna_sobrando_2\n",
        encoding="utf-8",
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert resultado is None
    assert "estrutura" in motivo.lower() or "colunas" in motivo.lower()


def test_arquivo_csv_malformado_parser_error_e_rejeitado(tmp_path):
    caminho = tmp_path / "quebrado.csv"
    caminho.write_text(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário\n"
        "05/01/2026;P-1;Centro;Mouse;Acessórios;2;89,90\n"
        "06/01/2026;P-2;Sul;Teclado;Acessórios;1;100,00;extra_1;extra_2\n",
        encoding="utf-8",
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert resultado is None
    assert "estrutura" in motivo.lower() or "csv" in motivo.lower()


def test_arquivo_com_cabecalho_duplicado_e_rejeitado(tmp_path):
    caminho = tmp_path / "cabecalho_duplicado.csv"
    caminho.write_text(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário;Preço Unitário\n"
        "05/01/2026;P-1;Centro;Mouse;Acessórios;1;10,00;99,00\n",
        encoding="utf-8",
    )

    resultado, motivo = ler_arquivo_csv_individual(caminho)
    assert resultado is None
    assert "duplicadas" in motivo.lower()
    assert "Preço Unitário" in motivo


def test_arquivo_com_cabecalho_ambiguo_por_espacos_ou_vazio_e_rejeitado(tmp_path):
    caminho_espacos = tmp_path / "cabecalho_espacos.csv"
    caminho_espacos.write_text(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário; Preço Unitário \n"
        "05/01/2026;P-1;Centro;Mouse;Acessórios;1;10,00;99,00\n",
        encoding="utf-8",
    )
    res_espacos, motivo_espacos = ler_arquivo_csv_individual(caminho_espacos)
    assert res_espacos is None
    assert "duplicadas" in motivo_espacos.lower()

    caminho_vazio = tmp_path / "cabecalho_coluna_vazia.csv"
    caminho_vazio.write_text(
        "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário;\n"
        "05/01/2026;P-1;Centro;Mouse;Acessórios;1;10,00;extra\n",
        encoding="utf-8",
    )
    res_vazio, motivo_vazio = ler_arquivo_csv_individual(caminho_vazio)
    assert res_vazio is None
    assert "sem nome" in motivo_vazio.lower()
