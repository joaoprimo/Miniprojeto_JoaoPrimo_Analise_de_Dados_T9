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
    imprimir("\nFim da execução.")


if __name__ == "__main__":
    main()
