"""
Pipeline de previsão de ANÁLISE a partir de Nota_leit + Comentleitura,
usando embeddings CONGELADOS do BERTimbau para representar o texto do
comentário (em vez de TextVectorization + Embedding treinados do zero).

Divisão de trabalho:
- bertimbau_embeddings.py: transforma texto em vetores (768 dimensões),
  com cache em disco (só processa comentário novo uma vez).
- este script: treina uma rede pequena e rápida (Dense) que combina
  [nota + embedding do comentário] -> ANÁLISE.

Onde rodar cada parte:
- A extração de embeddings é a parte pesada -> rode em casa, com GPU,
  principalmente na primeira vez (1M+ comentários). Runs seguintes são
  rápidos por causa do cache incremental.
- O treino da rede Dense em si é leve e rápido, roda bem até em CPU.
- Para inferência de comentários novos no trabalho (só CPU): o BERTimbau
  ainda precisa rodar (forward, sem treino) para gerar o embedding do
  comentário novo -- em CPU isso é mais lento que GPU, mas ainda viável
  para poucos comentários por vez (uso interativo). Se o volume mensal
  for muito grande, rode a extração de embeddings em casa antes e leve
  só os vetores prontos para o trabalho.
"""

import glob
import json
import os
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import class_weight
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import Concatenate, Dense, Embedding, Flatten, Input
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical

from bertimbau_embeddings import obter_embeddings_com_cache

# =========================================================
# CONFIGURAÇÃO
# =========================================================
CONFIG = {
    "padrao_treino": "data/processed/mvc_000*_test.csv",
    "excluir_arquivos": ["AGO"],
    "arquivo_alvo": "data/new/mvc_0003_AGO_01.csv",
    "modelo_path": "melhor_modelo_bertimbau.keras",
    "encoders_path": "encoders_bertimbau.json",
    "embeddings_cache_path": "embeddings_cache.joblib",
    "saida_path": "avaliado_01_ago_bertimbau.xlsx",
    "grafico_loss_path": "curva_perda_bertimbau.png",
    "embedding_model_name": "neuralmind/bert-base-portuguese-cased",
    "embedding_dim": 768,  # dimensão de saída do bert-base
    "embedding_max_length": 128,
    "embedding_batch_size": 32,
    "epochs": 30,
    "batch_size": 256,
    "unk_token": "__UNK__",
}

# ========================
# Funções auxiliares (iguais à versão anterior)
# ========================

def normalizar_colunas(df):
    df.columns = [
        col.strip().replace("\n", "").replace("\r", "").replace(".", "").replace(" ", "_")
        for col in df.columns
    ]
    return df


def carregar_dados_treino(caminho_pattern, excluir_arquivos=None):
    excluir_arquivos = excluir_arquivos or []
    arquivos = [arq for arq in glob.glob(caminho_pattern) if all(exc not in arq for exc in excluir_arquivos)]
    dfs = []
    for arq in arquivos:
        print(f"Lendo treino: {arq}")
        df = pd.read_csv(arq, sep=";", dtype={"Nº Serie": str})
        df = normalizar_colunas(df)
        dfs.append(df)
    if not dfs:
        raise ValueError("Nenhum arquivo de treino encontrado.")
    return pd.concat(dfs, ignore_index=True)


def carregar_dados_alvo(caminho_arquivo):
    print(f"Lendo alvo: {caminho_arquivo}")
    df = pd.read_csv(caminho_arquivo, sep=";")
    df = normalizar_colunas(df)
    df = df[df["Data"].notnull() & (df["Data"] != "")]
    return df


def salvar_encoders(le_nota, le_target, embedding_model_name, caminho):
    payload = {
        "nota_classes": list(le_nota.classes_),
        "target_classes": list(le_target.classes_),
        "embedding_model_name": embedding_model_name,
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def carregar_encoders(caminho):
    with open(caminho, encoding="utf-8") as f:
        payload = json.load(f)
    le_nota = LabelEncoder()
    le_nota.classes_ = np.array(payload["nota_classes"])
    le_target = LabelEncoder()
    le_target.classes_ = np.array(payload["target_classes"])
    return le_nota, le_target, payload.get("embedding_model_name")


def transform_com_unk(le, valores, unk_token):
    classes_conhecidas = set(le.classes_)
    valores_tratados = [v if v in classes_conhecidas else unk_token for v in valores]
    return le.transform(valores_tratados)


def preparar_encoders(df_completo, df_train, cfg):
    notas_com_unk = list(pd.unique(df_completo["Nota_leit"])) + [cfg["unk_token"]]
    le_nota = LabelEncoder().fit(notas_com_unk)
    le_target = LabelEncoder().fit(df_train["ANÁLISE"])
    return le_nota, le_target


def preparar_dados(df, cfg, encoders=None):
    df = df.copy()
    df["Nota_leit"] = df["Nota_leit"].astype(str)
    df["Comentleitura"] = df["Comentleitura"].astype(str)

    df_train = df[df["ANÁLISE"].notnull()].copy()
    df_pred = df[df["ANÁLISE"].isnull()].copy()

    if encoders is None:
        le_nota, le_target = preparar_encoders(df, df_train, cfg)
    else:
        le_nota, le_target = encoders["le_nota"], encoders["le_target"]

    df_train["nota_enc"] = transform_com_unk(le_nota, df_train["Nota_leit"], cfg["unk_token"])
    y = le_target.transform(df_train["ANÁLISE"])
    y_cat = to_categorical(y, num_classes=len(le_target.classes_))

    if not df_pred.empty:
        df_pred["nota_enc"] = transform_com_unk(le_nota, df_pred["Nota_leit"], cfg["unk_token"])
        X_pred_nota = df_pred["nota_enc"].values
        X_pred_coment_texto = df_pred["Comentleitura"].tolist()
    else:
        X_pred_nota = None
        X_pred_coment_texto = None

    X_train_nota = df_train["nota_enc"].values
    X_train_coment_texto = df_train["Comentleitura"].tolist()

    encoders = {"le_nota": le_nota, "le_target": le_target}
    return (
        X_train_nota, X_train_coment_texto, y_cat, y, encoders,
        X_pred_nota, X_pred_coment_texto, df_pred,
    )


# ========================
# Modelo (agora recebe embedding pronto, não texto cru)
# ========================

def criar_modelo(n_nota, n_classes, embedding_dim):
    input_nota = Input(shape=(1,), name="nota_input")
    input_coment_emb = Input(shape=(embedding_dim,), name="coment_embedding_input")

    emb_nota = Embedding(input_dim=n_nota, output_dim=8)(input_nota)
    emb_nota = Flatten()(emb_nota)

    # Projeta o embedding de 768 dimensões do BERTimbau para um espaço
    # menor, aprendendo a destacar o que importa para ESTA tarefa
    # específica (o BERTimbau em si não foi ajustado para ela).
    texto_proj = Dense(128, activation="relu")(input_coment_emb)
    texto_proj = Dense(64, activation="relu")(texto_proj)

    x = Concatenate()([emb_nota, texto_proj])
    x = Dense(64, activation="relu")(x)
    x = Dense(32, activation="relu")(x)
    output = Dense(n_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs=[input_nota, input_coment_emb], outputs=output)
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    return model


# ========================
# Pipeline principal
# ========================

def main():
    cfg = CONFIG

    df_treino = carregar_dados_treino(cfg["padrao_treino"], cfg["excluir_arquivos"])
    df_alvo = carregar_dados_alvo(cfg["arquivo_alvo"])
    df_completo = pd.concat([df_treino, df_alvo], ignore_index=True)

    (
        X_train_nota, X_train_coment_texto, y_cat, y_int, encoders,
        X_pred_nota, X_pred_coment_texto, df_pred,
    ) = preparar_dados(df_completo, cfg)

    le_nota, le_target = encoders["le_nota"], encoders["le_target"]

    # ---- Gera (ou recupera do cache) os embeddings do BERTimbau ----
    print("\n--- Gerando embeddings de treino (com cache) ---")
    X_train_emb = obter_embeddings_com_cache(
        X_train_coment_texto,
        cache_path=cfg["embeddings_cache_path"],
        model_name=cfg["embedding_model_name"],
        max_length=cfg["embedding_max_length"],
        batch_size=cfg["embedding_batch_size"],
    )

    X_pred_emb = None
    if X_pred_coment_texto:
        print("\n--- Gerando embeddings de previsão (com cache) ---")
        X_pred_emb = obter_embeddings_com_cache(
            X_pred_coment_texto,
            cache_path=cfg["embeddings_cache_path"],
            model_name=cfg["embedding_model_name"],
            max_length=cfg["embedding_max_length"],
            batch_size=cfg["embedding_batch_size"],
        )

    # Filtra classes com menos de 2 amostras (necessário para stratify)
    counts = Counter(y_int)
    classes_validas = {cls for cls, cnt in counts.items() if cnt >= 2}
    classes_descartadas = set(counts) - classes_validas
    if classes_descartadas:
        nomes_descartados = [le_target.classes_[c] for c in classes_descartadas]
        print(f"Aviso: classes com <2 amostras foram descartadas do treino: {nomes_descartados}")

    indices_validos = [i for i, label in enumerate(y_int) if label in classes_validas]
    X_train_nota = X_train_nota[indices_validos]
    X_train_emb = X_train_emb[indices_validos]
    y_cat = y_cat[indices_validos]
    y_int = y_int[indices_validos]

    X_nota_train, X_nota_val, X_emb_train, X_emb_val, y_train, y_val = train_test_split(
        X_train_nota, X_train_emb, y_cat, test_size=0.2, stratify=y_int, random_state=42
    )

    class_weights = dict(
        zip(
            np.unique(y_int),
            class_weight.compute_class_weight(class_weight="balanced", classes=np.unique(y_int), y=y_int),
        )
    )
    print("Pesos das classes:", class_weights)

    n_nota = len(le_nota.classes_)
    n_classes = y_cat.shape[1]

    modelo_valido_encontrado = False
    if os.path.exists(cfg["modelo_path"]) and os.path.exists(cfg["encoders_path"]):
        print("Modelo salvo encontrado. Verificando compatibilidade...")
        le_nota_salvo, le_target_salvo, embedding_model_salvo = carregar_encoders(cfg["encoders_path"])
        compativel = (
            len(le_nota_salvo.classes_) == n_nota
            and len(le_target_salvo.classes_) == n_classes
            and embedding_model_salvo == cfg["embedding_model_name"]
        )
        if compativel:
            print("Compatível. Carregando modelo salvo (sem retreinar).")
            model = load_model(cfg["modelo_path"])
            le_nota, le_target = le_nota_salvo, le_target_salvo
            modelo_valido_encontrado = True
        else:
            print("Modelo salvo é INCOMPATÍVEL com os dados/config atuais. Retreinando do zero.")

    if not modelo_valido_encontrado:
        model = criar_modelo(n_nota, n_classes, embedding_dim=cfg["embedding_dim"])

        early_stop = EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True)
        checkpoint_cb = ModelCheckpoint(
            filepath=cfg["modelo_path"], save_best_only=True, monitor="val_loss", mode="min", verbose=1
        )

        print("Treinando modelo (rápido -- só a rede Dense, embeddings já prontos)...")
        history = model.fit(
            {"nota_input": X_nota_train, "coment_embedding_input": X_emb_train},
            y_train,
            validation_data=({"nota_input": X_nota_val, "coment_embedding_input": X_emb_val}, y_val),
            epochs=cfg["epochs"],
            batch_size=cfg["batch_size"],
            verbose=1,
            callbacks=[early_stop, checkpoint_cb],
            class_weight=class_weights,
        )
        print("Treinamento finalizado e modelo salvo.")
        salvar_encoders(le_nota, le_target, cfg["embedding_model_name"], cfg["encoders_path"])

        plt.figure()
        plt.plot(history.history["loss"], label="loss")
        plt.plot(history.history["val_loss"], label="val_loss")
        plt.legend()
        plt.title("Curva de Perda (BERTimbau + Dense)")
        plt.xlabel("Época")
        plt.ylabel("Loss")
        plt.savefig(cfg["grafico_loss_path"])
        print(f"Gráfico de perda salvo em {cfg['grafico_loss_path']}")

        y_val_pred_probs = model.predict({"nota_input": X_nota_val, "coment_embedding_input": X_emb_val})
        y_val_pred = y_val_pred_probs.argmax(axis=1)
        y_val_true = y_val.argmax(axis=1)
        target_names_filtrados = [le_target.classes_[i] for i in sorted(np.unique(y_int))]

        print("\nRelatório de Classificação (Validação):")
        print(classification_report(y_val_true, y_val_pred, target_names=target_names_filtrados))
        print(f"F1 macro: {f1_score(y_val_true, y_val_pred, average='macro'):.4f}")
        print(f"F1 weighted: {f1_score(y_val_true, y_val_pred, average='weighted'):.4f}")

    if X_pred_nota is not None and X_pred_emb is not None:
        pred_probs = model.predict({"nota_input": X_pred_nota, "coment_embedding_input": X_pred_emb})
        y_pred_idx = pred_probs.argmax(axis=1)
        confiancas = pred_probs.max(axis=1)
        y_pred = le_target.inverse_transform(y_pred_idx)

        df_pred = df_pred.copy()
        df_pred["ANÁLISE"] = y_pred
        df_pred["confianca_previsao"] = confiancas
        df_pred["revisar_manualmente"] = confiancas < 0.6
        df_resultado = df_pred
        print(f"\n{df_resultado['revisar_manualmente'].sum()} casos marcados para revisão manual (confiança < 0.6).")
    else:
        df_resultado = df_alvo

    df_resultado.to_excel(cfg["saida_path"], index=False)
    print(f"Resultado salvo com sucesso em {cfg['saida_path']}.")


if __name__ == "__main__":
    main()