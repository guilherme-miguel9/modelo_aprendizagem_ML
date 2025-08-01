import polars as pl
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# ===== 1. Ler arquivos =====
df_treino = pl.read_csv("data/new/mvc_0001_test.csv", separator=';')
df_alvo = pl.read_csv("data/new/mvc_0002_test.csv", separator=';')

# ===== 2. Padronizar nomes das colunas =====
def normalizar_colunas(df):
    return df.rename({col: col.strip().replace('\n', '').replace('\r', '').replace('.', '').replace(' ', '_') for col in df.columns})

df_treino = normalizar_colunas(df_treino)
df_alvo = normalizar_colunas(df_alvo)

print(df_alvo.columns)
print(df_treino.columns)

# ===== 3. Codificar as colunas categóricas =====
df_treino = df_treino.with_columns([
    pl.col("Comentleitura").cast(pl.Categorical).alias("Comentleitura_cat"),
    pl.col("Nota_leit").cast(pl.Categorical).alias("Nota_leit_cat"),
]).with_columns([
    pl.col("Comentleitura_cat").to_physical().alias("Comentleitura_encoded"),
    pl.col("Nota_leit_cat").to_physical().alias("Nota_leit_encoded"),
])

df_alvo = df_alvo.with_columns([
    pl.col("Comentleitura").cast(pl.Categorical).alias("Comentleitura_cat"),
    pl.col("Nota_leit").cast(pl.Categorical).alias("Nota_leit_cat"),
]).with_columns([
    pl.col("Comentleitura_cat").to_physical().alias("Comentleitura_encoded"),
    pl.col("Nota_leit_cat").to_physical().alias("Nota_leit_encoded"),
])

# ===== 4. Treinar o modelo apenas com df_treino =====
df_treino_pd = df_treino.to_pandas()
df_treino_pd = df_treino_pd[df_treino_pd["ANÁLISE"].notna()]
X_train = df_treino_pd[["Comentleitura_encoded", "Nota_leit_encoded"]]
y_train = df_treino_pd["ANÁLISE"]

modelo = RandomForestClassifier(n_estimators=100, random_state=42)
modelo.fit(X_train, y_train)

# ===== 5. Prever apenas as linhas com ANÁLISE vazia no df_alvo =====
df_alvo_pd = df_alvo.to_pandas()
df_para_preencher = df_alvo_pd[df_alvo_pd["ANÁLISE"].isnull()]
df_mantidos = df_alvo_pd[df_alvo_pd["ANÁLISE"].notnull()]

X_pred = df_para_preencher[["Comentleitura_encoded", "Nota_leit_encoded"]].fillna(-1)
y_pred = modelo.predict(X_pred)

df_para_preencher["ANÁLISE"] = y_pred

# ===== 6. Juntar os dados preenchidos + os que já estavam preenchidos =====
df_resultado = pd.concat([df_mantidos, df_para_preencher], ignore_index=True)

# ===== 7. Salvar resultado final =====
df_resultado.to_excel("avaliados_completos.xlsx", index=False)

