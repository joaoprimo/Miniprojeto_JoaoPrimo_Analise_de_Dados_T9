# Como executar: Miniprojeto_JoaoPrimo_Analise_de_Dados_T9

Projeto de análise exploratória da base Varejo (Kaggle). O script é o `analise_varejo.py`.

## Opção A: VS Code (ou terminal)

1. Baixe a base em <https://www.kaggle.com/datasets/namespaiva/base-varejo/data> e coloque o arquivo na pasta `dados/` (pode ser o `.zip` do Kaggle, não precisa descompactar).
2. Instale as bibliotecas: `pip install -r requirements.txt`
3. Rode: `python analise_varejo.py`

## Opção B: Google Colab

1. Abra <https://colab.research.google.com>, crie um notebook e, no painel de arquivos (ícone de pasta), envie `analise_varejo.py` e a base do Kaggle.
2. Em uma célula, rode:
   ```
   !pip install -q pandas matplotlib
   !python analise_varejo.py
   ```

## O que acontece

- O relatório completo aparece no terminal (leva uns 25 segundos e usa cerca de 1 GB de memória).
- Os arquivos gerados ficam em `saida/`: `df_limpo.csv`, `relatorio_terminal.txt` e 3 gráficos `.png`.
- Se a base não for encontrada, o script avisa onde ela deve ficar.

Testado com Python 3.10 e 3.12, pandas 2.2.3 e 3.0.

A explicação do projeto, as decisões de limpeza, os insights e a reflexão sobre ETL estão no `README.md`.
