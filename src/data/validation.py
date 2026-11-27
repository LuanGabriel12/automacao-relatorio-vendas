"""Camada de validação de qualidade de dados comerciais com precisão Decimal."""

from decimal import Decimal, InvalidOperation

import pandas as pd

from src.config import COLUNAS_NEGOCIO_DUPLICATA, FORMATO_DATA_BR


def converter_texto_para_decimal_br(texto):
    """Converte texto numérico no padrão brasileiro diretamente para Decimal.

    Regras estritas para evitar alterações silenciosas de valores malformados:
    - Aceita opcionalmente sinal negativo inicial (ex.: ``-2``, ``-10,50``).
    - Separador de milhar ``.`` só é aceito em grupos exatos de 3 dígitos
      (ex.: ``3.499,90`` ou ``1.000``). Valores como ``12.34`` são rejeitados.
    - Separador decimal é ``,`` seguido por dígitos ASCII.
    - Rejeita notação científica, underscores, espaços internos, ``inf``, ``nan``.
    - Constrói ``Decimal`` diretamente da string normalizada, sem usar ``float``.
    """
    if texto is None:
        return None

    texto_limpo = str(texto).strip()
    if texto_limpo == "":
        return None

    texto_minusculo = texto_limpo.lower()
    if (
        "e" in texto_minusculo
        or "_" in texto_limpo
        or " " in texto_limpo
        or "+" in texto_limpo
        or "inf" in texto_minusculo
        or "nan" in texto_minusculo
    ):
        return None

    sinal = ""
    corpo = texto_limpo
    if corpo.startswith("-"):
        sinal = "-"
        corpo = corpo[1:]

    if corpo == "" or "-" in corpo:
        return None

    partes_decimais = corpo.split(",")
    if len(partes_decimais) > 2:
        return None

    parte_inteira = partes_decimais[0]
    parte_fracionaria = partes_decimais[1] if len(partes_decimais) == 2 else None

    if parte_inteira == "":
        return None

    if "." in parte_inteira:
        grupos = parte_inteira.split(".")
        primeiro_grupo = grupos[0]
        if (
            not primeiro_grupo.isascii()
            or not primeiro_grupo.isdigit()
            or len(primeiro_grupo) < 1
            or len(primeiro_grupo) > 3
            or primeiro_grupo.startswith("0")
        ):
            return None

        for grupo in grupos[1:]:
            if not grupo.isascii() or not grupo.isdigit() or len(grupo) != 3:
                return None

        inteira_sem_milhar = "".join(grupos)
    else:
        if not parte_inteira.isascii() or not parte_inteira.isdigit():
            return None
        inteira_sem_milhar = parte_inteira

    if parte_fracionaria is not None:
        if (
            parte_fracionaria == ""
            or not parte_fracionaria.isascii()
            or not parte_fracionaria.isdigit()
        ):
            return None
        texto_canonico = f"{sinal}{inteira_sem_milhar}.{parte_fracionaria}"
    else:
        texto_canonico = f"{sinal}{inteira_sem_milhar}"

    try:
        valor = Decimal(texto_canonico)
    except InvalidOperation:
        return None

    if not valor.is_finite():
        return None

    return valor


def converter_quantidade_br(texto):
    """Converte texto de quantidade brasileira para inteiro exato ou retorna None.

    Rejeita valores com vírgula decimal (ex.: ``1,5`` ou ``2,0``), textos
    malformados, infinitos ou não inteiros.
    """
    if texto is None:
        return None

    texto_limpo = str(texto).strip()
    if texto_limpo == "" or "," in texto_limpo:
        return None

    valor_decimal = converter_texto_para_decimal_br(texto_limpo)
    if valor_decimal is None:
        return None

    return int(valor_decimal)


def converter_preco_br(texto):
    """Converte texto de preço unitário brasileiro diretamente para Decimal."""
    return converter_texto_para_decimal_br(texto)


def _identificar_pedidos_conflitantes(df):
    """Identifica pedidos com Data ou Loja divergentes entre linhas/arquivos.

    Premissa de negócio: o identificador ``Pedido`` é globalmente único em toda a
    base de entrada; portanto, um mesmo pedido não pode possuir datas ou lojas
    diferentes. Todas as linhas do pedido conflitante são marcadas como inválidas.
    """
    pedidos_conflito_data = set()
    pedidos_conflito_loja = set()

    filtro_pedido_e_data = (df["_pedido"] != "") & df["_data_dt"].notna()
    if filtro_pedido_e_data.any():
        contagem_datas = (
            df.loc[filtro_pedido_e_data]
            .groupby("_pedido")["_data_dt"]
            .nunique()
        )
        pedidos_conflito_data = set(contagem_datas.loc[contagem_datas > 1].index)

    filtro_pedido_e_loja = (df["_pedido"] != "") & (df["_loja"] != "")
    if filtro_pedido_e_loja.any():
        contagem_lojas = (
            df.loc[filtro_pedido_e_loja]
            .groupby("_pedido")["_loja"]
            .nunique()
        )
        pedidos_conflito_loja = set(contagem_lojas.loc[contagem_lojas > 1].index)

    return pedidos_conflito_data, pedidos_conflito_loja


def _identificar_alertas_pedido_produto(df_validas):
    """Identifica ocorrências válidas de mesmo Pedido + Produto com atributos distintos.

    Por regra de negócio, essas ocorrências NÃO são rejeitadas automaticamente,
    pois podem representar itens legítimos em um pedido (ex.: lotes ou preços
    promocionais distintos) na ausência de um identificador único de linha.
    """
    alertas = []
    if len(df_validas) == 0:
        return alertas

    mascara_repetidos = df_validas.duplicated(
        subset=["_pedido", "_produto"],
        keep=False,
    )
    df_repetidos = df_validas.loc[mascara_repetidos]
    if len(df_repetidos) == 0:
        return alertas

    agrupado = df_repetidos.groupby(["_pedido", "_produto"])
    for (pedido, produto), grupo in agrupado:
        if len(grupo) > 1:
            quantidades = sorted(set(int(q) for q in grupo["_quantidade"]))
            precos = sorted(set(str(p).replace(".", ",") for p in grupo["_preco_unitario"]))
            categorias = sorted(set(str(c) for c in grupo["_categoria"]))
            arquivos = sorted(set(str(a) for a in grupo["Arquivo de origem"]))
            alertas.append(
                {
                    "pedido": str(pedido),
                    "produto": str(produto),
                    "ocorrencias": int(len(grupo)),
                    "quantidades_encontradas": quantidades,
                    "precos_encontrados": precos,
                    "categorias_encontradas": categorias,
                    "arquivos_origem": arquivos,
                    "observacao": (
                        "Mesmo Pedido + Produto com quantidade, preço ou categoria "
                        "distintos; mantido como válido para investigação devido à "
                        "ausência de identificador único de linha."
                    ),
                }
            )

    return alertas


def validar_vendas(dados_brutos):
    """Executa todas as regras de qualidade de dados sobre os registros consolidados.

    Preserva integralmente os valores originais recebidos nos CSVs, acumula
    múltiplos motivos na mesma linha sem duplicar a contagem de registros e
    identifica alertas de investigação para Pedido + Produto recorrentes.
    """
    df = dados_brutos.copy().reset_index(drop=True)
    total_registros = len(df)

    if total_registros == 0:
        df["Motivo"] = ""
        df["Quantidade de problemas"] = 0
        df["Status"] = ""
        return {
            "dados_validados": df,
            "total_registros_recebidos": 0,
            "total_registros_validos": 0,
            "total_registros_rejeitados": 0,
            "total_linhas_multiplos_erros": 0,
            "taxa_rejeicao_pct": Decimal("0.00"),
            "contagem_motivos": {},
            "alertas_investigacao": [],
            "pedidos_conflito_data": [],
            "pedidos_conflito_loja": [],
        }

    # Colunas normalizadas de trabalho (mantendo as colunas originais intactas)
    data_texto = df["Data"].str.strip()
    df["_data_dt"] = pd.to_datetime(
        data_texto,
        format=FORMATO_DATA_BR,
        errors="coerce",
    )
    df["_pedido"] = df["Pedido"].str.strip()
    df["_loja"] = df["Loja"].str.strip()
    df["_produto"] = df["Produto"].str.strip()
    df["_categoria"] = df["Categoria"].str.strip()

    quantidades_texto = df["Quantidade"].str.strip()
    precos_texto = df["Preço Unitário"].str.strip()

    quantidades_convertidas = [converter_quantidade_br(v) for v in quantidades_texto]
    precos_convertidos = [converter_preco_br(v) for v in precos_texto]

    # Armazena como dtype="object" para evitar coerção silenciosa para float64
    # quando há mistura de inteiros grandes (> 2^53) com None.
    df["_quantidade"] = pd.DataFrame(
        {"_quantidade": quantidades_convertidas}, dtype="object"
    )["_quantidade"]
    df["_preco_unitario"] = pd.DataFrame(
        {"_preco_unitario": precos_convertidos}, dtype="object"
    )["_preco_unitario"]

    motivos_por_linha = [[] for _ in range(total_registros)]

    # Etapa 1: Validações de campo por linha (acumula todos os erros encontrados)
    datas_dt_lista = list(df["_data_dt"])
    datas_txt_lista = list(data_texto)
    pedidos_lista = list(df["_pedido"])
    lojas_lista = list(df["_loja"])
    produtos_lista = list(df["_produto"])
    categorias_lista = list(df["_categoria"])
    qtd_txt_lista = list(quantidades_texto)
    preco_txt_lista = list(precos_texto)

    for indice in range(total_registros):
        motivos = motivos_por_linha[indice]

        if datas_txt_lista[indice] == "":
            motivos.append("Data ausente")
        elif pd.isna(datas_dt_lista[indice]):
            motivos.append("Data inválida")

        if pedidos_lista[indice] == "":
            motivos.append("Pedido ausente")

        if lojas_lista[indice] == "":
            motivos.append("Loja ausente")

        if produtos_lista[indice] == "":
            motivos.append("Produto ausente")

        if categorias_lista[indice] == "":
            motivos.append("Categoria ausente")

        if qtd_txt_lista[indice] == "":
            motivos.append("Quantidade ausente")
        elif quantidades_convertidas[indice] is None:
            motivos.append("Quantidade inválida (formato não inteiro ou inválido)")
        elif quantidades_convertidas[indice] <= 0:
            motivos.append("Quantidade inválida (menor ou igual a zero)")

        if preco_txt_lista[indice] == "":
            motivos.append("Preço ausente")
        elif precos_convertidos[indice] is None:
            motivos.append("Preço inválido (formato inválido ou não finito)")
        elif precos_convertidos[indice] <= Decimal("0"):
            motivos.append("Preço inválido (menor ou igual a zero)")

    # Etapa 2: Conflitos de cabeçalho do pedido (Data ou Loja divergente)
    pedidos_conflito_data, pedidos_conflito_loja = _identificar_pedidos_conflitantes(df)

    if len(pedidos_conflito_data) > 0:
        mascara_conflito_data = df["_pedido"].isin(pedidos_conflito_data)
        for indice in df.loc[mascara_conflito_data].index:
            motivos_por_linha[indice].append("Pedido conflitante (Data divergente)")

    if len(pedidos_conflito_loja) > 0:
        mascara_conflito_loja = df["_pedido"].isin(pedidos_conflito_loja)
        for indice in df.loc[mascara_conflito_loja].index:
            motivos_por_linha[indice].append("Pedido conflitante (Loja divergente)")

    # Etapa 3: Duplicatas exatas entre registros que passaram nas regras anteriores
    # Política preservada da V1 (adotada para este conjunto sem chave única de linha)
    indices_candidatos = [
        indice for indice in range(total_registros) if len(motivos_por_linha[indice]) == 0
    ]
    if len(indices_candidatos) > 0:
        candidatos = df.loc[indices_candidatos]
        mascara_duplicadas = candidatos.duplicated(
            subset=COLUNAS_NEGOCIO_DUPLICATA,
            keep="first",
        )
        for indice in candidatos.loc[mascara_duplicadas].index:
            motivos_por_linha[indice].append("Registro duplicado")

    # Etapa 4: Consolidação dos motivos e classificação Válido / Inválido (sem NumPy)
    df["Motivo"] = ["; ".join(lista) for lista in motivos_por_linha]
    df["Quantidade de problemas"] = [len(lista) for lista in motivos_por_linha]
    df["Status"] = "Válido"
    df.loc[df["Motivo"] != "", "Status"] = "Inválido"

    # Etapa 5: Alertas de investigação (mesmo Pedido + Produto válido com atributos distintos)
    df_validas_internas = df.loc[df["Status"] == "Válido"]
    alertas_investigacao = _identificar_alertas_pedido_produto(df_validas_internas)

    # Estatísticas de qualidade
    contagem_motivos = {}
    total_linhas_multiplos_erros = 0
    for lista in motivos_por_linha:
        if len(lista) > 1:
            total_linhas_multiplos_erros += 1
        for motivo in lista:
            contagem_motivos[motivo] = contagem_motivos.get(motivo, 0) + 1

    total_validos = int((df["Status"] == "Válido").sum())
    total_rejeitados = int((df["Status"] == "Inválido").sum())
    taxa_rejeicao_pct = (
        (Decimal(total_rejeitados) * Decimal("100")) / Decimal(total_registros)
    )

    return {
        "dados_validados": df,
        "total_registros_recebidos": total_registros,
        "total_registros_validos": total_validos,
        "total_registros_rejeitados": total_rejeitados,
        "total_linhas_multiplos_erros": total_linhas_multiplos_erros,
        "taxa_rejeicao_pct": taxa_rejeicao_pct,
        "contagem_motivos": contagem_motivos,
        "alertas_investigacao": alertas_investigacao,
        "pedidos_conflito_data": sorted(pedidos_conflito_data),
        "pedidos_conflito_loja": sorted(pedidos_conflito_loja),
    }
