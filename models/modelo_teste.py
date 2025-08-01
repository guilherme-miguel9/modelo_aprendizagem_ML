import polars as pl
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
import pandas as pd
import os

caminho_pasta = "data/new/"
arquivos_csv = [f for f in os.listdir(caminho_pasta) if f.endswith(".csv")]

dfs = []

for arquivo in arquivos_csv:
    caminho_arquivo = os.path.join(caminho_pasta, arquivo)
    df_temp = pl.read_csv(caminho_arquivo, separator=';', truncate_ragged_lines=True)
    dfs.append(df_temp)

df = pl.concat(dfs, how="vertical")

df = df.rename({col: col.strip().replace('\n', '').replace('\r', '') for col in df.columns})
df = df.rename({col: col.strip().replace('.', '').replace(' ', '_') for col in df.columns})

df = (
    df.with_columns([
        pl.col("Comentleitura").cast(pl.Categorical).alias("Comentleitura_cat"),
        pl.col("Nota_leit").cast(pl.Categorical).alias("Nota_leit_cat"),
    ])
    .with_columns([
        pl.col("Comentleitura_cat").to_physical().alias("Comentleitura_encoded"),
        pl.col("Nota_leit_cat").to_physical().alias("Nota_leit_encoded"),
    ])
)

df_train = df.filter(pl.col("ANÁLISE").is_not_null())
df_predict = df.filter(pl.col("ANÁLISE").is_null())

df_train_pd = df_train.to_pandas()
df_predict_pd = df_predict.to_pandas()

X_train = df_train_pd[["Comentleitura_encoded", "Nota_leit_encoded"]]
y_train = df_train_pd["ANÁLISE"]
X_predict = df_predict_pd[["Comentleitura_encoded", "Nota_leit_encoded"]]



X_train = X_train.fillna(-1)
X_predict = X_predict.fillna(-1)


#=========================================================================================

#X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

# Treinamento do modelo
modelo = RandomForestClassifier(n_estimators=100, random_state=42)
modelo.fit(X_train, y_train)

y_pred = modelo.predict(X_predict)

df_predict_pd.loc[:, "ANÁLISE"] = y_pred

df_predict_pd = df_predict_pd.reset_index(drop=True)
df_predict_pd.to_excel("avaliados_pelo_modelo.xlsx", index=False)
