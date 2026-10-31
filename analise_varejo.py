#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mini-Projeto Avaliativo - Módulo 1 - Análise de Dados com Python [T9]
Análise Exploratória de Dados (AED) da base Varejo (Kaggle: namespaiva/base-varejo)

Aluno: João Primo            Turma: Analise_de_Dados_T9

Como executar (VS Code):   python analise_varejo.py
Como executar (Colab):     envie o script e a base, depois:  !python analise_varejo.py
Requisitos:                pandas (obrigatório) e matplotlib (opcional, só para os gráficos)

A base (Base Varejo.csv, Base_Varejo.csv ou Varejo.csv) pode estar na pasta do script,
em ./dados/ ou na pasta atual. Se o arquivo for o .zip baixado do Kaggle (mesmo com
extensão .csv), o script abre o zip sozinho.

Dicionário de dados (base original):
    DATA        data da compra (dd/mm/aaaa)
    CO_ID       identificador da compra (uma compra = vários itens)
    CL_ID       identificador do cliente
    CL_GENERO   gênero do cliente (M/F)
    CL_EC       estado civil do cliente (código 1 a 5; a base não traz a legenda)
    CL_FHL      número de filhos do cliente
    CL_SEG      segmento / classe do cliente (A, B, C)
    PR_ID       identificador do produto
    PR_CAT      categoria do produto
    PR_NOME     nome do produto
A base NÃO tem preço nem quantidade. Por isso "vendas" aqui significa volume de itens
vendidos e "compras" significa número de CO_ID distintos.

Organização do script (um bloco por Sprint do enunciado):
    Sprint 1 - Importação (csv.DictReader -> pandas) e visão geral
    Sprint 2 - Funções de limpeza (texto, inteiro, decimal, datetime) com regex
    Sprint 3 - Diagnóstico de qualidade + limpeza (nulos, duplicatas, tipos)
    Sprint 4 - Estatística descritiva do número de filhos
    Sprint 5 - Agrupamentos, gráficos, conclusões e relatório final no terminal
    Sprint 6 - Gravação do df_limpo.csv e do relatório
"""

import csv
import io
import re
import sys
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

# ----------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ----------------------------------------------------------------------------
try:
    PASTA_PROJETO = Path(__file__).resolve().parent
except NameError:  # ocorre se o código for colado em uma célula do Colab
    PASTA_PROJETO = Path.cwd()

PASTA_SAIDA = PASTA_PROJETO / "saida"
NOMES_ARQUIVO = ["Base Varejo.csv", "Base_Varejo.csv", "Base_varejo.csv", "Varejo.csv"]
COLUNAS = [
    "DATA", "CO_ID", "CL_ID", "CL_GENERO", "CL_EC",
    "CL_FHL", "CL_SEG", "PR_ID", "PR_CAT", "PR_NOME",
]

# Linhas impressas no terminal; guardadas para salvar o relatório em arquivo (Sprint 6)
LINHAS_RELATORIO = []


def imprimir(texto=""):
    """Mostra o texto no terminal e guarda uma cópia para o relatório em arquivo."""
    print(texto)
    LINHAS_RELATORIO.append(str(texto))


def titulo(texto):
    """Imprime um título de seção destacado."""
    imprimir()
    imprimir("=" * 78)
    imprimir(texto)
    imprimir("=" * 78)


def br(valor, casas=0):
    """Formata número no padrão brasileiro (1.234.567,89)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "#").replace(".", ",").replace("#", ".")


def fmt_df(df, casas=2):
    """Converte um DataFrame em texto, com números no padrão brasileiro."""
    saida = df.copy()
    for coluna in saida.columns:
        if pd.api.types.is_integer_dtype(saida[coluna]):
            saida[coluna] = saida[coluna].map(lambda x: br(x))
        elif pd.api.types.is_float_dtype(saida[coluna]):
            saida[coluna] = saida[coluna].map(lambda x: br(x, casas))
    return saida.to_string()


# ----------------------------------------------------------------------------
# SPRINT 1 - IMPORTAÇÃO DOS DADOS
# ----------------------------------------------------------------------------
def localizar_base():
    """Procura o arquivo da base nas pastas mais comuns (projeto, dados/, Colab)."""
    pastas = [
        PASTA_PROJETO, PASTA_PROJETO / "dados",
        Path.cwd(), Path.cwd() / "dados",
        Path("/content"), Path("/content/dados"),
    ]
    for pasta in pastas:  # 1o: nomes conhecidos
        for nome in NOMES_ARQUIVO:
            caminho = pasta / nome
            if caminho.is_file():
                return caminho
    for pasta in pastas:  # 2o: qualquer csv que tenha "varejo" no nome
        if pasta.is_dir():
            for caminho in sorted(pasta.glob("*.csv")):
                if "arejo" in caminho.name.lower():
                    return caminho
    raise FileNotFoundError(
        "Base não encontrada. Baixe em https://www.kaggle.com/datasets/namespaiva/base-varejo "
        "e coloque o arquivo na pasta 'dados/' (ou ao lado do script)."
    )


def _ler_linhas(arquivo_texto):
    """
    Lê o CSV com csv.DictReader (módulo nativo do Python).
    O cabeçalho do arquivo termina com ';;;;' (4 colunas sem nome e vazias). Para não
    perder essa informação do diagnóstico, as colunas sem nome recebem um nome
    provisório (SEM_NOME_n), são contadas e descartadas da lista de registros.
    """
    cabecalho = next(csv.reader(arquivo_texto, delimiter=";"))
    nomes = [(nome.strip() or f"SEM_NOME_{i}") for i, nome in enumerate(cabecalho, start=1)]

    faltando = [c for c in COLUNAS if c not in nomes]
    if faltando:
        raise ValueError(f"Colunas esperadas não encontradas no arquivo: {faltando}")

    extras = [n for n in nomes if n not in COLUNAS]
    preenchidas = {n: 0 for n in extras}  # quantas linhas tem algum valor nas colunas extras

    registros = []
    for linha in csv.DictReader(arquivo_texto, fieldnames=nomes, delimiter=";"):
        registros.append({c: linha[c] for c in COLUNAS})
        for nome in extras:
            if (linha[nome] or "").strip():
                preenchidas[nome] += 1
    return registros, nomes, preenchidas


def ler_base_dictreader(caminho):
    """Abre o arquivo (csv comum ou zip do Kaggle) e devolve os registros lidos."""
    if zipfile.is_zipfile(caminho):
        with zipfile.ZipFile(caminho) as pacote:
            interno = next(n for n in pacote.namelist() if n.lower().endswith(".csv"))
            imprimir(f"Aviso: '{caminho.name}' é um .zip; lendo '{interno}' de dentro dele.")
            with pacote.open(interno) as bruto:
                with io.TextIOWrapper(bruto, encoding="utf-8-sig", newline="") as arquivo:
                    return _ler_linhas(arquivo)
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        return _ler_linhas(arquivo)


def etapa_importacao():
    """Sprint 1: importa a base e mostra registros, colunas e tipos de dados."""
    titulo("SPRINT 1 - IMPORTAÇÃO DA BASE (csv.DictReader -> pandas)")
    caminho = localizar_base()
    imprimir(f"Arquivo da base: {caminho}")

    registros, cabecalho, extras = ler_base_dictreader(caminho)
    df = pd.DataFrame(registros)  # tudo chega como texto; os tipos são ajustados no Sprint 3

    imprimir(f"Número de registros (linhas): {br(len(df))}")
    imprimir(f"Colunas no arquivo: {len(cabecalho)} "
             f"({len(COLUNAS)} com nome + {len(extras)} sem nome)")
    imprimir(f"Colunas carregadas: {', '.join(df.columns)}")
    imprimir("\nTipos de dados logo após a leitura (tudo texto):")
    imprimir(df.dtypes.astype(str).to_string())
    imprimir("\nPrimeiras 5 linhas:")
    imprimir(df.head().to_string())
    return df, cabecalho, extras


# ----------------------------------------------------------------------------
# SPRINT 2 - FUNÇÕES DE LIMPEZA (TEXTO, INTEIRO, DECIMAL, DATETIME)
# ----------------------------------------------------------------------------
# Textos que, na prática, significam "valor vazio". "#N/D" é o erro de PROCV do Excel
# e aparece de verdade nas colunas PR_CAT e PR_NOME desta base.
TOKENS_NULOS = {"", "NULL", "NONE", "NAN", "N/A", "NA", "#N/D", "#N/A", "#VALOR!", "#REF!", "-"}


def limpar_texto(valor):
    """Padroniza texto: remove acentos, espaços repetidos/pontas e usa MAIÚSCULAS."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = texto.encode("ascii", "ignore").decode("ascii")  # tira acentos (ex.: LIMAO)
    texto = re.sub(r"\s+", " ", texto)                        # vários espaços -> um
    return texto.strip().upper()


def eh_nulo(valor):
    """True se o valor, depois de padronizado, for um dos marcadores de vazio."""
    return limpar_texto(valor) in TOKENS_NULOS


def limpar_inteiro(valor):
    """Converte texto em int. Devolve None se for vazio ou não numérico."""
    texto = limpar_texto(valor)
    if texto in TOKENS_NULOS:
        return None
    texto = re.sub(r"[^\d-]", "", texto)  # mantém só dígitos e sinal
    if not re.fullmatch(r"-?\d+", texto):
        return None
    return int(texto)


def limpar_decimal(valor):
    """Converte texto em float, aceitando formato brasileiro (R$ 1.234,56)."""
    texto = limpar_texto(valor)
    if texto in TOKENS_NULOS:
        return None
    texto = re.sub(r"[^\d,.\-]", "", texto)  # remove R$, espaços etc.
    if "," in texto:                          # 1.234,56 -> 1234.56
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def converter_data(valor):
    """Converte 'dd/mm/aaaa' em datetime (módulo datetime). Data inválida -> None."""
    try:
        return datetime.strptime(limpar_texto(valor), "%d/%m/%Y")
    except ValueError:
        return None


def aplicar_por_unicos(serie, funcao):
    """
    Aplica a função só nos valores DISTINTOS e depois espalha o resultado.
    A base tem 830 mil linhas mas poucos valores distintos por coluna; isso torna a
    limpeza muito mais rápida do que chamar a função linha a linha.
    """
    mapa = {valor: funcao(valor) for valor in serie.unique()}
    return serie.map(mapa)


def demonstrar_funcoes():
    """Mostra as funções de limpeza em ação com exemplos simples."""
    titulo("SPRINT 2 - FUNÇÕES DE LIMPEZA (demonstração)")
    exemplos = [
        ("limpar_texto('  refrigerante   limaO ')", limpar_texto("  refrigerante   limaO ")),
        ("limpar_texto('Limão')", limpar_texto("Limão")),
        ("eh_nulo('#N/D')", eh_nulo("#N/D")),
        ("limpar_inteiro(' 1.234 ')", limpar_inteiro(" 1.234 ")),
        ("limpar_inteiro('abc')", limpar_inteiro("abc")),
        ("limpar_decimal('R$ 1.234,56')", limpar_decimal("R$ 1.234,56")),
        ("converter_data('19/08/2022')", converter_data("19/08/2022")),
        ("converter_data('31/02/2022')", converter_data("31/02/2022")),
    ]
    for chamada, resultado in exemplos:
        imprimir(f"  {chamada:<40} -> {resultado!r}")


# ----------------------------------------------------------------------------
# SPRINT 3 - DIAGNÓSTICO E LIMPEZA (NULOS, DUPLICATAS, TIPOS)
# ----------------------------------------------------------------------------
COLUNAS_CHAVE = ["DATA", "CO_ID", "CL_ID", "PR_ID"]
COLUNAS_CLIENTE = ["CL_GENERO", "CL_EC", "CL_FHL", "CL_SEG"]
COLUNAS_INTEIRAS = {"CO_ID": "int32", "CL_ID": "int32", "PR_ID": "int32",
                    "CL_EC": "int8", "CL_FHL": "int8"}
COLUNAS_CATEGORIA = ["CL_GENERO", "CL_SEG", "PR_CAT", "PR_NOME"]


def checar(descricao, quantidade, detalhe=""):
    """Imprime uma verificação de qualidade: [OK] se zero ocorrências, senão [PROBLEMA]."""
    status = "[OK]      " if quantidade == 0 else "[PROBLEMA]"
    imprimir(f"  {status} {descricao}: {br(quantidade)} {detalhe}".rstrip())


def diagnostico(df, extras):
    """Mostra nulos, duplicatas e inconsistências da base BRUTA, antes de limpar."""
    titulo("SPRINT 3 - DIAGNÓSTICO DE QUALIDADE (dados brutos)")
    total = len(df)
    nulos_tokens = list(TOKENS_NULOS - {""})

    # (1) Nulos por coluna: vazio ("") e marcadores de erro (#N/D etc.)
    imprimir("1) Valores nulos por coluna:")
    linhas = []
    for coluna in COLUNAS:
        padronizado = aplicar_por_unicos(df[coluna], limpar_texto)
        vazios = int((padronizado == "").sum())
        marcadores = int(padronizado.isin(nulos_tokens).sum())
        linhas.append({"coluna": coluna, "vazios": vazios, "marcador_erro": marcadores,
                       "total_nulos": vazios + marcadores,
                       "pct": (vazios + marcadores) / total * 100})
    for nome, preenchidas in extras.items():
        vazios = total - preenchidas
        linhas.append({"coluna": nome, "vazios": vazios, "marcador_erro": 0,
                       "total_nulos": vazios, "pct": vazios / total * 100})
    imprimir(fmt_df(pd.DataFrame(linhas).set_index("coluna")))

    # (2) Duplicatas: linhas totalmente iguais
    duplicadas = int(df.duplicated().sum())
    imprimir("\n2) Duplicatas (linhas 100% iguais a outra):")
    checar("linhas duplicadas", duplicadas, f"({br(duplicadas / total * 100, 2)}% da base)")

    # (3) Inconsistências e regras de negócio
    imprimir("\n3) Inconsistências e regras de negócio:")
    datas = aplicar_por_unicos(df["DATA"], converter_data)
    checar("datas inválidas (fora de dd/mm/aaaa)", int(datas.isna().sum()))
    validas = pd.to_datetime(datas.dropna())
    checar("datas no futuro", int((validas > datetime.now()).sum()),
           f"| período: {validas.min():%d/%m/%Y} a {validas.max():%d/%m/%Y}")

    categoria = aplicar_por_unicos(df["PR_CAT"], limpar_texto)
    checar("categorias vazias ou com erro (#N/D)", int(categoria.isin(TOKENS_NULOS).sum()))
    nome = aplicar_por_unicos(df["PR_NOME"], limpar_texto)
    checar("nomes de produto vazios ou com erro (#N/D)", int(nome.isin(TOKENS_NULOS).sum()))

    fora_padrao = 0
    exemplos = []
    for coluna in COLUNAS_CATEGORIA:
        ruins = [v for v in df[coluna].unique() if v != limpar_texto(v)]
        fora_padrao += int(df[coluna].isin(ruins).sum())
        exemplos += ruins[:2]
    checar("textos fora do padrão (caixa/espaços/acento)", fora_padrao,
           f"ex.: {exemplos[:2]}" if exemplos else "")

    genero = aplicar_por_unicos(df["CL_GENERO"], limpar_texto)
    checar("gênero fora de M/F", int((~genero.isin(["M", "F"])).sum()))
    segmento = aplicar_por_unicos(df["CL_SEG"], limpar_texto)
    checar("segmento fora de A/B/C", int((~segmento.isin(["A", "B", "C"])).sum()))
    filhos = aplicar_por_unicos(df["CL_FHL"], limpar_inteiro)
    checar("número de filhos inválido (não numérico ou fora de 0 a 20)",
           int((filhos.isna() | (filhos < 0) | (filhos > 20)).sum()))

    # Regra do identificador de compra: cada CO_ID representa UMA compra de UM cliente em UMA data
    por_compra = df.groupby("CO_ID")[["CL_ID", "DATA"]].nunique()
    conflito = int(((por_compra["CL_ID"] > 1) | (por_compra["DATA"] > 1)).sum())
    checar("CO_ID ligado a mais de 1 cliente ou data (regra da compra)", conflito,
           f"| {br(len(por_compra))} compras distintas")
    por_cliente = df.groupby("CL_ID")[COLUNAS_CLIENTE].nunique()
    checar("clientes com atributos conflitantes (gênero/EC/filhos/segmento)",
           int((por_cliente > 1).any(axis=1).sum()), f"| {br(len(por_cliente))} clientes")
    por_produto = df.groupby("PR_ID")[["PR_NOME", "PR_CAT"]].nunique()
    checar("PR_ID com mais de 1 nome ou categoria", int((por_produto > 1).any(axis=1).sum()),
           f"| {br(len(por_produto))} produtos (PR_ID)")


def preencher_se_nulo(valor, rotulo):
    """Regra if/else do enunciado: valor vazio vira o rótulo (ex.: 'Sem Categoria')."""
    if valor in TOKENS_NULOS:
        return rotulo
    else:
        return valor


def limpar_base(df_bruto, extras):
    """
    Limpeza mínima em 3 etapas (nulos, duplicatas, tipos).
    Devolve o df limpo e um dicionário de contadores para o relatório final.
    """
    titulo("SPRINT 3 - LIMPEZA DA BASE")
    df = df_bruto.copy()
    c = {"linhas_lidas": len(df), "colunas_vazias_removidas": len(extras)}

    # ---- ETAPA 1: padronizar texto e tratar nulos ------------------------------------
    imprimir("ETAPA 1 - Nulos e padronização de texto")
    imprimir(f"  - {len(extras)} colunas sem nome e 100% vazias foram descartadas na leitura.")
    for coluna in COLUNAS:
        df[coluna] = aplicar_por_unicos(df[coluna], limpar_texto)

    # Categoria e nome vazios: NÃO removemos a linha (é uma venda real); rotulamos.
    c["ids_sem_categoria"] = sorted(df.loc[df["PR_CAT"].isin(TOKENS_NULOS), "PR_ID"].unique())
    c["categorias_preenchidas"] = int(df["PR_CAT"].isin(TOKENS_NULOS).sum())
    c["nomes_preenchidos"] = int(df["PR_NOME"].isin(TOKENS_NULOS).sum())
    df["PR_CAT"] = aplicar_por_unicos(df["PR_CAT"], lambda v: preencher_se_nulo(v, "Sem Categoria"))
    df["PR_NOME"] = aplicar_por_unicos(df["PR_NOME"], lambda v: preencher_se_nulo(v, "Sem Nome"))
    imprimir(f"  - PR_CAT vazio/#N/D -> 'Sem Categoria': {br(c['categorias_preenchidas'])} linhas")
    imprimir(f"  - PR_NOME vazio/#N/D -> 'Sem Nome': {br(c['nomes_preenchidos'])} linhas")
    imprimir("    Escolha: manter a linha e rotular, porque o item foi vendido de verdade;")
    imprimir("    apagar distorceria o volume por categoria e por compra. Não há como adivinhar a")
    imprimir(f"    categoria correta (PR_ID afetado(s): {', '.join(c['ids_sem_categoria']) or 'nenhum'}), então imputar a moda")
    imprimir("    seria inventar informação.")

    # Colunas-chave (DATA, CO_ID, CL_ID, PR_ID) nulas: sem elas a linha não é analisável -> remove.
    lista_nulos = list(TOKENS_NULOS)
    sem_chave = df[COLUNAS_CHAVE].isin(lista_nulos).any(axis=1)

    # Atributos do cliente nulos: o cliente é sempre o mesmo, então imputamos o valor
    # que ele tem nas outras linhas (CL_ID -> atributo é constante); se não houver, remove.
    for coluna in COLUNAS_CLIENTE:
        df[coluna] = df[coluna].where(~df[coluna].isin(lista_nulos))
        df[coluna] = df[coluna].fillna(df.groupby("CL_ID")[coluna].transform("first"))
    sem_atributo = df[COLUNAS_CLIENTE].isna().any(axis=1)

    removidas = int((sem_chave | sem_atributo).sum())
    df = df[~(sem_chave | sem_atributo)]
    c["removidas_por_nulo"] = removidas
    imprimir(f"  - Linhas removidas por chave/atributo nulo sem como imputar: {br(removidas)}")

    # ---- ETAPA 2: duplicatas ----------------------------------------------------------
    imprimir("\nETAPA 2 - Duplicatas")
    mascara_dup = df.duplicated()
    c["duplicadas_removidas"] = int(mascara_dup.sum())
    c["compras_com_duplicata"] = int(df.loc[mascara_dup, "CO_ID"].nunique())
    # Linhas iguais ficam sempre dentro do MESMO CO_ID: a mesma compra trouxe o mesmo produto
    # mais de uma vez. Como a base não tem coluna de quantidade, tratamos isso como
    # "unidades". Eliminamos as repetições, mas guardamos quantas eram na coluna QTD.
    df = (df.groupby(COLUNAS, sort=False, as_index=False, dropna=False)
            .size().rename(columns={"size": "QTD"}))
    imprimir(f"  - Linhas duplicadas eliminadas: {br(c['duplicadas_removidas'])} "
             f"({br(c['duplicadas_removidas'] / c['linhas_lidas'] * 100, 2)}% da base), "
             f"em {br(c['compras_com_duplicata'])} compras")
    imprimir("  - Nova coluna QTD = quantas vezes cada linha aparecia (nenhum item é perdido:")
    imprimir(f"    soma de QTD = {br(int(df['QTD'].sum()))}; maior QTD em uma linha = {int(df['QTD'].max())}).")
    imprimir("    Hipótese: repetição dentro da mesma compra = mais de uma unidade do produto.")

    # ---- ETAPA 3: tipos de dados ------------------------------------------------------
    imprimir("\nETAPA 3 - Ajuste de tipos")
    df["DATA"] = pd.to_datetime(aplicar_por_unicos(df["DATA"], converter_data))
    for coluna in COLUNAS_INTEIRAS:
        df[coluna] = aplicar_por_unicos(df[coluna], limpar_inteiro)
    invalidas = df[["DATA"] + list(COLUNAS_INTEIRAS)].isna().any(axis=1)
    c["removidas_por_formato"] = int(df.loc[invalidas, "QTD"].sum())
    df = df[~invalidas]
    imprimir(f"  - Linhas com data/número em formato inválido removidas: {br(c['removidas_por_formato'])}")

    for coluna, tipo in COLUNAS_INTEIRAS.items():
        df[coluna] = df[coluna].astype(tipo)
    df["QTD"] = df["QTD"].astype("int16")
    for coluna in COLUNAS_CATEGORIA:
        df[coluna] = df[coluna].astype("category")

    # Colunas derivadas da data (usadas nas análises temporais)
    df["ANO"] = df["DATA"].dt.year.astype("int16")
    df["MES"] = df["DATA"].dt.month.astype("int8")
    df["ANO_MES"] = df["DATA"].dt.strftime("%Y-%m")
    ordem = ["DATA", "ANO", "MES", "ANO_MES", "CO_ID", "CL_ID", "CL_GENERO", "CL_EC",
             "CL_FHL", "CL_SEG", "PR_ID", "PR_CAT", "PR_NOME", "QTD"]
    df = df[ordem].reset_index(drop=True)
    imprimir("  - DATA convertida para datetime64 (datetime.strptime, formato dd/mm/aaaa).")
    imprimir("  - IDs, estado civil e filhos convertidos para inteiros; texto para category.")
    imprimir("  - Colunas criadas: ANO, MES, ANO_MES.")

    # ---- Conferência final ------------------------------------------------------------
    c["itens_totais"] = int(df["QTD"].sum())
    assert df.isna().sum().sum() == 0, "ainda existem nulos no df limpo"
    assert c["itens_totais"] == c["linhas_lidas"] - c["removidas_por_nulo"] - c["removidas_por_formato"]
    imprimir("\nConferência: 0 nulos no df limpo e soma de QTD bate com as linhas lidas "
             "menos as removidas.")
    imprimir(f"Antes: {br(c['linhas_lidas'])} linhas x {len(df_bruto.columns) + len(extras)} colunas"
             f"   |   Depois: {br(len(df))} linhas x {df.shape[1]} colunas")
    imprimir("\nTipos de dados do df limpo:")
    imprimir(df.dtypes.astype(str).to_string())
    return df, c


# ----------------------------------------------------------------------------
# SPRINT 4 - ESTATÍSTICA DESCRITIVA: NÚMERO DE FILHOS (CL_FHL)
# ----------------------------------------------------------------------------
def resumo_estatistico(serie):
    """Calcula todos os parâmetros pedidos para uma série numérica."""
    quartis = serie.quantile([0.25, 0.50, 0.75])
    moda = serie.mode().tolist()  # pode haver mais de uma moda
    return {
        "contagem": int(serie.count()),
        "média": float(serie.mean()),
        "mediana": float(serie.median()),
        "desvio padrão": float(serie.std()),
        "moda": moda,
        "mínimo": int(serie.min()),
        "q1 (25%)": float(quartis[0.25]),
        "q2 (50%)": float(quartis[0.50]),
        "q3 (75%)": float(quartis[0.75]),
        "máximo": int(serie.max()),
    }


def estatisticas_filhos(df):
    """Sprint 4: estatísticas da coluna de número de filhos, por cliente e por compra."""
    titulo("SPRINT 4 - ESTATÍSTICA DESCRITIVA: NÚMERO DE FILHOS DO CLIENTE (CL_FHL)")
    # Número de filhos é atributo do CLIENTE. Se usássemos as linhas da base, quem compra mais
    # pesaria mais. Por isso a visão principal usa 1 linha por cliente; a visão por compra
    # (1 linha por CO_ID) fica ao lado só para comparação.
    visoes = {
        "POR CLIENTE (1 linha por CL_ID) - visão principal": df.drop_duplicates("CL_ID")["CL_FHL"],
        "POR COMPRA (1 linha por CO_ID) - comparação": df.drop_duplicates("CO_ID")["CL_FHL"],
    }
    resultado = {}
    for nome, serie in visoes.items():
        stats = resumo_estatistico(serie)
        descr = serie.describe()  # conferência cruzada com o describe() do pandas
        assert abs(descr["mean"] - stats["média"]) < 1e-9 and abs(descr["50%"] - stats["mediana"]) < 1e-9
        imprimir(f"\n{nome}")
        for rotulo, valor in stats.items():
            if rotulo == "moda":
                texto = ", ".join(str(m) for m in valor)
            elif isinstance(valor, float):
                texto = br(valor, 3)
            else:
                texto = br(valor)
            imprimir(f"  {rotulo:<15} {texto:>10}")
        resultado[nome] = stats
    imprimir("\n(conferido com Series.describe() do pandas: média e mediana batem)")

    clientes = visoes["POR CLIENTE (1 linha por CL_ID) - visão principal"]
    distribuicao = clientes.value_counts().sort_index().to_frame("clientes")
    distribuicao["pct"] = distribuicao["clientes"] / distribuicao["clientes"].sum() * 100
    imprimir("\nDistribuição de clientes por número de filhos:")
    imprimir(fmt_df(distribuicao))
    return {"cliente": resultado["POR CLIENTE (1 linha por CL_ID) - visão principal"],
            "compra": resultado["POR COMPRA (1 linha por CO_ID) - comparação"],
            "distribuicao": distribuicao}


# ----------------------------------------------------------------------------
# SPRINT 5 - AGRUPAMENTOS, GRÁFICOS, CONCLUSÕES E RELATÓRIO FINAL
# ----------------------------------------------------------------------------
PRODUTOS_INFANTIS = ["FRALDA", "CHUPETA", "MORDEDOR", "PAPINHA INFANTIL"]


def agrupamentos(df):
    """Explora padrões com groupby() e pivot_table(). 'itens' = soma de QTD."""
    titulo("SPRINT 5 - AGRUPAMENTOS (groupby / pivot_table)")
    r = {}
    total_compras = df["CO_ID"].nunique()

    # 1) Gênero: quem compra mais?
    genero = df.groupby("CL_GENERO", observed=True).agg(
        itens=("QTD", "sum"), compras=("CO_ID", "nunique"), clientes=("CL_ID", "nunique"))
    genero["itens_por_compra"] = genero["itens"] / genero["compras"]
    genero["pct_itens"] = genero["itens"] / genero["itens"].sum() * 100
    imprimir("1) Por gênero do cliente:")
    imprimir(fmt_df(genero))
    r["genero"] = genero

    # 2) Categoria: o que mais vende? (penetração = % das compras que levam a categoria)
    categoria = df.groupby("PR_CAT", observed=True).agg(
        itens=("QTD", "sum"), compras=("CO_ID", "nunique"))
    categoria["pct_itens"] = categoria["itens"] / categoria["itens"].sum() * 100
    categoria["penetracao_compras"] = categoria["compras"] / total_compras * 100
    categoria = categoria.sort_values("itens", ascending=False)
    imprimir("\n2) Por categoria do produto:")
    imprimir(fmt_df(categoria))
    r["categoria"] = categoria

    # 3) Gênero x categoria (pivot_table): % de itens de cada categoria dentro do gênero
    cruzado = df.pivot_table(index="CL_GENERO", columns="PR_CAT", values="QTD",
                             aggfunc="sum", observed=True)
    cruzado = cruzado.div(cruzado.sum(axis=1), axis=0) * 100
    imprimir("\n3) Gênero x categoria (pivot_table) - % dos itens de cada gênero:")
    imprimir(fmt_df(cruzado))
    r["genero_categoria"] = cruzado
    r["mix_dif_max"] = float((cruzado.max() - cruzado.min()).max())  # maior diferença, em p.p.

    # 4) Evolução no tempo
    ano = df.groupby("ANO").agg(itens=("QTD", "sum"), compras=("CO_ID", "nunique"),
                                clientes_ativos=("CL_ID", "nunique"))
    imprimir("\n4) Evolução por ano (2022 vai só até 08/12/2022):")
    imprimir(fmt_df(ano))
    compras_mes = df.pivot_table(index="ANO", columns="MES", values="CO_ID",
                                 aggfunc="nunique", observed=True)
    imprimir("\n   Compras por ano x mês (pivot_table):")
    imprimir(fmt_df(compras_mes))
    itens_mes = df.groupby("ANO_MES")["QTD"].sum()
    r["ano"], r["compras_mes"], r["itens_mes"] = ano, compras_mes, itens_mes

    # 5) Número de filhos x comportamento de compra
    filhos = df.groupby("CL_FHL", observed=True).agg(
        clientes=("CL_ID", "nunique"), compras=("CO_ID", "nunique"), itens=("QTD", "sum"))
    filhos["itens_por_compra"] = filhos["itens"] / filhos["compras"]
    filhos["compras_por_cliente"] = filhos["compras"] / filhos["clientes"]
    imprimir("\n5) Por número de filhos do cliente:")
    imprimir(fmt_df(filhos))
    r["filhos"] = filhos
    r["ipc_filhos"] = (float(filhos["itens_por_compra"].min()), float(filhos["itens_por_compra"].max()))

    # 5b) Quem compra produtos infantis? Clientes com filhos deveriam concentrar esses itens.
    infantis = df[df["PR_NOME"].isin(PRODUTOS_INFANTIS)]
    itens_inf_sem_filhos = int(infantis.loc[infantis["CL_FHL"] == 0, "QTD"].sum())
    total_infantis = int(infantis["QTD"].sum())
    r["pct_infantis_sem_filhos"] = itens_inf_sem_filhos / total_infantis * 100 if total_infantis else float("nan")
    clientes_unicos = df.drop_duplicates("CL_ID")
    r["pct_clientes_sem_filhos"] = (clientes_unicos["CL_FHL"] == 0).mean() * 100
    imprimir(f"\n   Produtos infantis ({', '.join(PRODUTOS_INFANTIS)}):")
    imprimir(f"   {br(r['pct_infantis_sem_filhos'], 1)}% dos itens foram comprados por clientes SEM filhos,")
    imprimir(f"   que são {br(r['pct_clientes_sem_filhos'], 1)}% dos clientes.")

    # 6) Segmento
    segmento = df.groupby("CL_SEG", observed=True).agg(
        clientes=("CL_ID", "nunique"), compras=("CO_ID", "nunique"), itens=("QTD", "sum"))
    segmento["itens_por_compra"] = segmento["itens"] / segmento["compras"]
    segmento["compras_por_cliente"] = segmento["compras"] / segmento["clientes"]
    imprimir("\n6) Por segmento do cliente (CL_SEG):")
    imprimir(fmt_df(segmento))
    r["segmento"] = segmento

    # 7) Produtos e clientes de destaque
    por_nome = df[df["PR_NOME"] != "Sem Nome"].groupby("PR_NOME", observed=True).agg(
        itens=("QTD", "sum"), ids_distintos=("PR_ID", "nunique"))
    top_produtos = por_nome.sort_values("itens", ascending=False).head(5)
    imprimir("\n7) Top 5 produtos por nome (ids_distintos = quantos PR_ID usam o mesmo nome):")
    imprimir(fmt_df(top_produtos))
    por_cliente = df.groupby("CL_ID").agg(itens=("QTD", "sum"), compras=("CO_ID", "nunique"))
    por_cliente = por_cliente.sort_values("itens", ascending=False)
    top10_pct = por_cliente["itens"].head(len(por_cliente) // 10).sum() / por_cliente["itens"].sum() * 100
    imprimir("\n   Top 5 clientes por itens comprados:")
    imprimir(fmt_df(por_cliente.head(5)))
    imprimir(f"   Os 10% maiores clientes respondem por {br(top10_pct, 1)}% dos itens.")
    r["top_produtos"], r["top_clientes"], r["top10_pct"] = top_produtos, por_cliente, top10_pct
    r["por_nome"] = por_nome
    r["total_compras"] = total_compras
    return r


def gerar_graficos(df, estat):
    """Salva 3 gráficos simples em saída/ (só se o matplotlib estiver instalado)."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # não abre janela; apenas grava o arquivo
        import matplotlib.pyplot as plt
    except ImportError:
        imprimir("\n(matplotlib não instalado: gráficos ignorados. pip install matplotlib)")
        return []
    PASTA_SAIDA.mkdir(exist_ok=True)
    arquivos = []

    itens_cat = df.groupby("PR_CAT", observed=True)["QTD"].sum().sort_values()
    fig, eixo = plt.subplots(figsize=(8, 4))
    eixo.barh(itens_cat.index.astype(str), itens_cat.values / 1000, color="#2a6f97")
    eixo.set_title("Itens vendidos por categoria")
    eixo.set_xlabel("Itens (em milhares)")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "grafico_categorias.png", dpi=110)
    plt.close(fig)
    arquivos.append("grafico_categorias.png")

    compras_mes = df.groupby("ANO_MES")["CO_ID"].nunique()
    fig, eixo = plt.subplots(figsize=(10, 4))
    eixo.plot(compras_mes.index, compras_mes.values, color="#c1121f", marker="o", markersize=3)
    eixo.set_xticks(range(0, len(compras_mes), 3))
    eixo.set_xticklabels(compras_mes.index[::3], rotation=60, fontsize=8)
    eixo.set_title("Compras por mês")
    eixo.set_ylabel("Compras (CO_ID distintos)")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "grafico_compras_mes.png", dpi=110)
    plt.close(fig)
    arquivos.append("grafico_compras_mes.png")

    dist = estat["distribuicao"]
    fig, eixo = plt.subplots(figsize=(6, 4))
    eixo.bar(dist.index.astype(str), dist["clientes"], color="#588157")
    eixo.set_title("Clientes por número de filhos")
    eixo.set_xlabel("Número de filhos")
    eixo.set_ylabel("Clientes")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "grafico_filhos.png", dpi=110)
    plt.close(fig)
    arquivos.append("grafico_filhos.png")

    imprimir(f"\nGráficos salvos em saída/: {', '.join(arquivos)}")
    return arquivos


def relatorio_final(df, c, estat, r):
    """Contadores finais + bloco de conclusões (6 tópicos), tudo calculado a partir dos dados."""
    titulo("RELATÓRIO FINAL - CONTADORES")
    clientes_uni = df["CL_ID"].nunique()
    contadores = [
        ("Registros lidos", c["linhas_lidas"]),
        ("Colunas sem nome e vazias descartadas", c["colunas_vazias_removidas"]),
        ("Categorias vazias/#N/D -> 'Sem Categoria'", c["categorias_preenchidas"]),
        ("Nomes vazios/#N/D -> 'Sem Nome'", c["nomes_preenchidos"]),
        ("Linhas removidas por nulo sem imputação", c["removidas_por_nulo"]),
        ("Linhas duplicadas eliminadas (viraram QTD)", c["duplicadas_removidas"]),
        ("Linhas removidas por formato inválido", c["removidas_por_formato"]),
        ("Linhas do df limpo (itens distintos por compra)", len(df)),
        ("Itens vendidos (soma de QTD)", c["itens_totais"]),
        ("Compras (CO_ID)", r["total_compras"]),
        ("Clientes (CL_ID)", clientes_uni),
        ("Produtos (PR_ID)", df["PR_ID"].nunique()),
        ("Categorias (PR_CAT)", df["PR_CAT"].nunique()),
    ]
    for rotulo, valor in contadores:
        imprimir(f"  {rotulo:<52} {br(valor):>10}")
    imprimir(f"  {'Período':<52} {df['DATA'].min():%d/%m/%Y} a {df['DATA'].max():%d/%m/%Y}")

    # ---- números usados nas conclusões ----
    cat = r["categoria"]
    gen = r["genero"]
    mes = r["itens_mes"]
    compras_mes = r["compras_mes"]
    est = estat["cliente"]
    sem_cat_pct = cat["pct_itens"].get("Sem Categoria", 0.0)
    ids_txt = ", ".join(c["ids_sem_categoria"]) or "nenhum"
    ano = r["ano"]
    ano_pico = int(ano["itens"].idxmax())
    mes_max, mes_min = mes.idxmax(), mes.idxmin()
    # Meses com volume anormal: menos de 25% da mediana mensal de compras. O primeiro e o
    # último mês ficam de fora da regra porque a coleta pode ter começado/terminado no meio deles.
    compras_por_mes = df.groupby("ANO_MES")["CO_ID"].nunique()
    mediana_mes = float(compras_por_mes.median())
    interior = compras_por_mes.iloc[1:-1]
    meses_baixos = interior[interior < 0.25 * mediana_mes]
    lista_baixos = ", ".join(f"{m[5:]}/{m[:4]} ({n} compras)" for m, n in meses_baixos.items()) or "nenhum"
    ultimo_mes = compras_por_mes.index[-1]
    explicacao = "; é indício de falha de coleta, e não de queda real de vendas" if len(meses_baixos) else ""
    ex_nome = r["por_nome"]["ids_distintos"].idxmax()
    ex_ids = int(r["por_nome"].loc[ex_nome, "ids_distintos"])
    lider_genero = gen["pct_itens"].idxmax()
    dist = estat["distribuicao"]
    pct_sem_filhos = dist["pct"].get(0, 0.0)
    n_ids = df.loc[df["PR_NOME"] != "Sem Nome", "PR_ID"].nunique()
    n_nomes = df.loc[df["PR_NOME"] != "Sem Nome", "PR_NOME"].nunique()

    titulo("CONCLUSÕES (principais insights e problemas remanescentes)")
    conclusoes = [
        f"1) Alimentos dominam: {cat.index[0]} é {br(cat.iloc[0]['pct_itens'], 1)}% dos itens e está em "
        f"{br(cat.iloc[0]['penetracao_compras'], 1)}% das compras; {str(cat.index[1]).lower()} e "
        f"{str(cat.index[2]).lower()} vêm a seguir ({br(cat.iloc[1]['pct_itens'], 1)}% e "
        f"{br(cat.iloc[2]['pct_itens'], 1)}%). As {len(cat)} categorias "
        f"incluem 'Sem Categoria' ({br(sem_cat_pct, 2)}% dos itens; PR_ID: {ids_txt}).",
        f"2) Gênero: clientes do gênero {lider_genero} respondem por {br(gen['pct_itens'].max(), 1)}% dos itens "
        f"({int(gen.loc[lider_genero, 'clientes'])} dos {clientes_uni} clientes). O tamanho médio da compra "
        f"é praticamente igual ({br(gen['itens_por_compra'].min(), 1)} x {br(gen['itens_por_compra'].max(), 1)} itens) "
        f"e o mix de categorias difere no máximo {br(r['mix_dif_max'], 2)} ponto percentual entre os gêneros: "
        f"a diferença de volume vem do número de clientes de cada gênero, não de comprarem diferente.",
        f"3) Tempo: {ano_pico} foi o ano de maior volume ({br(int(ano.loc[ano_pico, 'itens']))} itens) e o "
        f"mês de pico foi {mes_max[5:]}/{mes_max[:4]} ({br(int(mes.max()))} itens). Meses com volume anormalmente "
        f"baixo (menos de 25% da mediana mensal de {br(mediana_mes)} compras): {lista_baixos}{explicacao}. "
        f"O último mês ({ultimo_mes[5:]}/{ultimo_mes[:4]}) é parcial: os dados terminam em {df['DATA'].max():%d/%m/%Y}.",
        f"4) Número de filhos (por cliente): média {br(est['média'], 2)}, mediana {br(est['mediana'], 0)}, "
        f"moda {', '.join(str(m) for m in est['moda'])}, desvio padrão {br(est['desvio padrão'], 2)}, "
        f"mínimo {est['mínimo']} e máximo {est['máximo']}; Q1={br(est['q1 (25%)'], 0)}, "
        f"Q3={br(est['q3 (75%)'], 0)}. {br(pct_sem_filhos, 1)}% dos clientes não têm filhos "
        f"(média > mediana: distribuição assimétrica à direita).",
        f"5) Filhos não explicam o comportamento de compra: {br(r['pct_infantis_sem_filhos'], 1)}% dos itens "
        f"infantis (fralda, chupeta etc.) são comprados por clientes SEM filhos, quase exatamente a "
        f"fração de clientes sem filhos ({br(r['pct_clientes_sem_filhos'], 1)}%). Os itens por compra variam só de "
        f"{br(r['ipc_filhos'][0], 1)} a {br(r['ipc_filhos'][1], 1)} entre os grupos de filhos e os 10% maiores "
        f"clientes respondem por {br(r['top10_pct'], 1)}% dos itens. Essa uniformidade sugere base sintética "
        f"ou sorteada, o que limita conclusões de negócio (é uma hipótese, não uma prova).",
        f"6) Problemas remanescentes: (a) sem preço/quantidade, 'vendas' é só volume de itens e QTD "
        f"depende da hipótese de que linha repetida = unidade extra; (b) {n_ids} PR_ID com nome para {n_nomes} nomes distintos "
        f"(ex.: {ex_nome} tem {ex_ids} IDs), então ranking por nome mistura SKUs; (c) CL_EC não tem "
        f"legenda; (d) PR_ID sem categoria/nome: {ids_txt}; (e) meses com volume anormalmente baixo: {lista_baixos}.",
    ]
    for texto in conclusoes:
        imprimir(texto)
        imprimir()


# ----------------------------------------------------------------------------
# EXECUÇÃO
# ----------------------------------------------------------------------------
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # evita erro de acento em terminais antigos
    PASTA_SAIDA.mkdir(exist_ok=True)

    df_bruto, cabecalho, extras = etapa_importacao()
    demonstrar_funcoes()
    diagnostico(df_bruto, extras)
    df, contadores = limpar_base(df_bruto, extras)
    estat = estatisticas_filhos(df)
    resultados = agrupamentos(df)
    gerar_graficos(df, estat)
    relatorio_final(df, contadores, estat, resultados)
    imprimir("\nFim da execução.")


if __name__ == "__main__":
    main()
