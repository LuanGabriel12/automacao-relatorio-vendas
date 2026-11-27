"""Fixtures compartilhadas para os testes automatizados do Sales Automation Engine V2."""

import pandas as pd
import pytest


CABECALHO_PADRAO = "Data;Pedido;Loja;Produto;Categoria;Quantidade;Preço Unitário"


@pytest.fixture
def criar_csv(tmp_path):
    """Cria arquivos CSV brasileiros em pasta temporária isolada."""

    def _criar(nome_arquivo, linhas, pasta=None, incluir_cabecalho=True, encoding="utf-8"):
        destino = pasta if pasta is not None else tmp_path
        destino.mkdir(parents=True, exist_ok=True)
        caminho = destino / nome_arquivo

        conteudo_linhas = []
        if incluir_cabecalho:
            conteudo_linhas.append(CABECALHO_PADRAO)
        conteudo_linhas.extend(linhas)

        texto = "\n".join(conteudo_linhas) + ("\n" if conteudo_linhas else "")
        caminho.write_text(texto, encoding=encoding, newline="\n")
        return caminho

    return _criar


@pytest.fixture
def dataframe_bruto_minimo():
    """Cria DataFrame bruto no formato produzido pela camada de ingestão."""

    def _construir(registros):
        linhas = []
        for indice, item in enumerate(registros, start=2):
            linha = {
                "Data": item.get("Data", "05/01/2026"),
                "Pedido": item.get("Pedido", f"P-{indice}"),
                "Loja": item.get("Loja", "Centro"),
                "Produto": item.get("Produto", "Mouse Sem Fio"),
                "Categoria": item.get("Categoria", "Acessórios"),
                "Quantidade": item.get("Quantidade", "1"),
                "Preço Unitário": item.get("Preço Unitário", "100,00"),
                "Arquivo de origem": item.get("Arquivo de origem", "teste.csv"),
                "Linha no arquivo": item.get("Linha no arquivo", indice),
            }
            linhas.append(linha)
        return pd.DataFrame(linhas)

    return _construir
