# Pasta `dados/`

Coloque aqui a base **Varejo** baixada do Kaggle:
<https://www.kaggle.com/datasets/namespaiva/base-varejo/data>

- Pode ser o `.csv` ou o `.zip` do Kaggle, **sem precisar descompactar**: o script abre o zip sozinho.
- Nomes aceitos: `Base Varejo.csv`, `Base_Varejo.csv`, `Base_varejo.csv`, `Varejo.csv`
  (ou qualquer `.csv` com "varejo" no nome).
- O script também procura o arquivo na mesma pasta do `analise_varejo.py`.

A base não está versionada no Git (está no `.gitignore`) porque vem do Kaggle.
O resultado da limpeza, esse sim, está versionado em `saida/df_limpo.csv`.
