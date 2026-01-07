import pandas as pd
from sklearn.neural_network import MLPClassifier

# Carrega os dados
df = pd.read_csv("dados_sofascore.csv", encoding='utf-16')

# Define X (entradas)
X = df[["posse_casa", "posse_fora", "chutes_casa", "chutes_fora"]]

# Define y (Aqui você precisaria adicionar uma coluna de 'resultado' no CSV manualmente por enquanto)
# y = df["resultado"] 

# Treina o modelo
# model = MLPClassifier(...).fit(X, y)