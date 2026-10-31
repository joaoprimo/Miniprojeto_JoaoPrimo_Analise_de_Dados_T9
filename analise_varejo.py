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
# EXECUÇÃO
# ----------------------------------------------------------------------------
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # evita erro de acento em terminais antigos
    PASTA_SAIDA.mkdir(exist_ok=True)

    df_bruto, cabecalho, extras = etapa_importacao()
    imprimir("\nFim da execução.")


if __name__ == "__main__":
    main()
