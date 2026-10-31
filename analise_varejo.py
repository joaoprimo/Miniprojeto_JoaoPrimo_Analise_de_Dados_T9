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
# EXECUÇÃO
# ----------------------------------------------------------------------------
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # evita erro de acento em terminais antigos
    PASTA_SAIDA.mkdir(exist_ok=True)

    df_bruto, cabecalho, extras = etapa_importacao()
    demonstrar_funcoes()
    imprimir("\nFim da execução.")


if __name__ == "__main__":
    main()
