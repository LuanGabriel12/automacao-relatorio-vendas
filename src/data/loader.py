"""Camada de ingestão dinâmica e validação estrutural de arquivos CSV."""

from pathlib import Path

import pandas as pd

from src.config import (
    CODIFICACAO_LEITURA,
    COLUNAS_OBRIGATORIAS,
    RAIZ_PROJETO,
    SEPARADOR_CSV,
)


def _formatar_caminho_relativo(pasta):
    """Retorna caminho relativo à raiz do projeto quando possível (portável entre SOs)."""
    caminho = Path(pasta).resolve()
    try:
        return caminho.relative_to(RAIZ_PROJETO.resolve()).as_posix()
    except ValueError:
        return caminho.name


def listar_arquivos_csv(pasta_entrada):
    """Lista arquivos CSV da pasta de entrada em ordem alfabética determinística."""
    pasta = Path(pasta_entrada)
    if not pasta.exists() or not pasta.is_dir():
        raise FileNotFoundError(f"Pasta de entrada não encontrada: {pasta}")

    arquivos = sorted(pasta.glob("*.csv"))
    return arquivos


def ler_arquivo_csv_individual(caminho_arquivo):
    """Lê e valida estruturalmente um arquivo CSV individual sem alterar valores brutos.

    Retorna uma tupla ``(dataframe, motivo_rejeicao)``. Quando o arquivo é aceito,
    ``motivo_rejeicao`` é ``None``; quando rejeitado, ``dataframe`` é ``None``.
    """
    caminho = Path(caminho_arquivo)

    if not caminho.exists() or not caminho.is_file():
        return None, "Arquivo não encontrado"

    if caminho.stat().st_size == 0:
        return None, "Arquivo vazio (0 bytes, sem cabeçalho nem dados)"

    try:
        cabecalho_df = pd.read_csv(
            caminho,
            sep=SEPARADOR_CSV,
            dtype=str,
            keep_default_na=False,
            encoding=CODIFICACAO_LEITURA,
            header=None,
            nrows=1,
        )
    except pd.errors.EmptyDataError:
        return None, "Arquivo vazio (sem cabeçalho nem dados)"
    except UnicodeDecodeError:
        return None, "Erro de codificação na leitura (esperado UTF-8)"
    except pd.errors.ParserError:
        return None, "Erro de estrutura/formatação CSV na leitura do arquivo"
    except OSError as erro:
        return None, f"Erro de leitura do arquivo: {erro}"

    if len(cabecalho_df) == 0:
        return None, "Arquivo vazio (sem cabeçalho nem dados)"

    cabecalho_bruto = [str(col) for col in cabecalho_df.loc[0]]
    if any(col.strip() == "" for col in cabecalho_bruto):
        return None, "Cabeçalho inválido: coluna sem nome detectada"

    vistos = set()
    colunas_duplicadas = []
    for col in cabecalho_bruto:
        chave = col.strip()
        if chave in vistos and chave not in colunas_duplicadas:
            colunas_duplicadas.append(chave)
        vistos.add(chave)

    if len(colunas_duplicadas) > 0:
        lista_duplicadas = ", ".join(colunas_duplicadas)
        return (
            None,
            f"Cabeçalho inválido: colunas duplicadas ou ambíguas ({lista_duplicadas})",
        )

    try:
        tabela = pd.read_csv(
            caminho,
            sep=SEPARADOR_CSV,
            dtype=str,
            keep_default_na=False,
            encoding=CODIFICACAO_LEITURA,
        )
    except pd.errors.EmptyDataError:
        return None, "Arquivo vazio (sem cabeçalho nem dados)"
    except UnicodeDecodeError:
        return None, "Erro de codificação na leitura (esperado UTF-8)"
    except pd.errors.ParserError:
        return None, "Erro de estrutura/formatação CSV na leitura do arquivo"
    except OSError as erro:
        return None, f"Erro de leitura do arquivo: {erro}"

    if not isinstance(tabela.index, pd.RangeIndex):
        return (
            None,
            "Erro de estrutura CSV: linhas contêm mais colunas do que o cabeçalho",
        )

    colunas_encontradas = list(tabela.columns)
    colunas_faltantes = [
        coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in colunas_encontradas
    ]
    if colunas_faltantes:
        lista_faltantes = ", ".join(colunas_faltantes)
        return (
            None,
            f"Colunas obrigatórias ausentes: {lista_faltantes} "
            f"(verifique também se o separador é '{SEPARADOR_CSV}')",
        )

    if len(tabela) == 0:
        return None, "Arquivo vazio (apenas cabeçalho, sem registros de vendas)"

    colunas_extras = [
        coluna for coluna in colunas_encontradas if coluna not in COLUNAS_OBRIGATORIAS
    ]

    tabela_padronizada = tabela.loc[:, COLUNAS_OBRIGATORIAS].copy()
    tabela_padronizada["Arquivo de origem"] = caminho.name
    tabela_padronizada["Linha no arquivo"] = list(range(2, len(tabela_padronizada) + 2))

    metadados = {
        "arquivo": caminho.name,
        "registros_lidos": len(tabela_padronizada),
        "colunas_extras_ignoradas": colunas_extras,
    }
    return (tabela_padronizada, metadados), None


def carregar_arquivos_entrada(pasta_entrada):
    """Descobre, valida e consolida todos os arquivos CSV da pasta de entrada.

    Arquivos individuais com erro estrutural (vazios, malformados, sem colunas
    obrigatórias) são registrados em ``arquivos_rejeitados`` sem descartar os
    arquivos válidos. Se a pasta não existir ou não contiver nenhum ``.csv``,
    levanta ``FileNotFoundError``.
    """
    arquivos = listar_arquivos_csv(pasta_entrada)
    if len(arquivos) == 0:
        raise FileNotFoundError(
            f"Nenhum arquivo CSV encontrado na pasta de entrada: {pasta_entrada}"
        )

    tabelas_aceitas = []
    arquivos_aceitos = []
    arquivos_rejeitados = []

    for caminho_arquivo in arquivos:
        resultado_leitura, motivo_rejeicao = ler_arquivo_csv_individual(caminho_arquivo)
        if motivo_rejeicao is not None:
            arquivos_rejeitados.append(
                {
                    "arquivo": caminho_arquivo.name,
                    "motivo": motivo_rejeicao,
                }
            )
        else:
            tabela, metadados = resultado_leitura
            tabelas_aceitas.append(tabela)
            arquivos_aceitos.append(metadados)

    if len(tabelas_aceitas) > 0:
        dados_brutos = pd.concat(tabelas_aceitas, ignore_index=True)
    else:
        colunas_vazias = COLUNAS_OBRIGATORIAS + ["Arquivo de origem", "Linha no arquivo"]
        dados_brutos = pd.DataFrame(columns=colunas_vazias)

    return {
        "pasta_entrada": _formatar_caminho_relativo(pasta_entrada),
        "dados_brutos": dados_brutos,
        "total_arquivos_encontrados": len(arquivos),
        "arquivos_aceitos": arquivos_aceitos,
        "arquivos_rejeitados": arquivos_rejeitados,
        "total_registros_recebidos": len(dados_brutos),
    }
