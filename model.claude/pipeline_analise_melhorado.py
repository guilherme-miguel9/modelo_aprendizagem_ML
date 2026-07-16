"""
Pipeline de previsão de ANÁLISE a partir de Nota_leit + Comentleitura.

Principais mudanças em relação à versão original:
1. LabelEncoders (le_nota, le_target) agora são salvos/carregados em disco
   (JSON) -- evita o bug de recriar os encoders do zero a cada execução,
   o que podia dessincronizar os índices de classe com o modelo salvo.
2. Notas (Nota_leit) nunca vistas no treino não quebram mais o script --
   caem numa categoria "__UNK__" tratada explicitamente.
3. Antes de reaproveitar um modelo salvo (.keras), o script confere se o
   número de classes/notas bate com o que o modelo espera. Se não bater,
   força retreino em vez de continuar com um mapeamento errado.
4. Trocado GlobalAveragePooling1D puro por um bloco Conv1D + GlobalMaxPooling1D
   antes da média -- captura padrões locais de ordem de palavras (ex.
   negações, "não X" vs "X"), que a média pura de embeddings ignora.
5. Métricas de avaliação agora incluem F1 macro/weighted (não só accuracy),
   mais adequado com classes desbalanceadas.
6. Gráfico de perda salvo em arquivo (plt.savefig) em vez de plt.show(),
   que trava em ambientes sem tela (servidores, cron, etc.).

Como usar: ajuste a seção CONFIG e rode o script normalmente.
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
from tensorflow.keras.layers import (
    Concatenate,
    Conv1D,
    Dense,
    Embedding,
    Flatten,
    GlobalAveragePooling1D,
    GlobalMaxPooling1D,
    Input,
    TextVectorization,
)
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical

# =========================================================
# CONFIGURAÇÃO
# =========================================================
CONFIG = {
    "padrao_treino": "data/processed/mvc_000*_test.csv",
    "excluir_arquivos": ["AGO"],
    "arquivo_alvo": "data/new/mvc_0003_AGO_01.csv",
    "modelo_path": "melhor_modelo_texto.keras",
    "encoders_path": "encoders.json",
    "saida_path": "avaliado_01_ago_nn_embedding.xlsx",
    "grafico_loss_path": "curva_perda.png",
    "max_tokens_vocab": 5000,
    "seq_length": 50,
    "epochs": 20,
    "batch_size": 256,
    "unk_token": "__UNK__",
}

# ========================
# Funções auxiliares
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


def salvar_encoders(le_nota, le_target, caminho):
    payload = {
        "nota_classes": list(le_nota.classes_),
        "target_classes": list(le_target.classes_),
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
    return le_nota, le_target


def transform_com_unk(le, valores, unk_token):
    """Transforma valores com LabelEncoder, mapeando valores nunca vistos
    para o token de categoria desconhecida (evita crash em produção)."""
    classes_conhecidas = set(le.classes_)
    valores_tratados = [v if v in classes_conhecidas else unk_token for v in valores]
    return le.transform(valores_tratados)


def preparar_encoders(df_completo, df_train, cfg):
    """Ajusta encoders novos garantindo que o token UNK exista sempre
    na lista de notas conhecidas (para casos futuros de nota nova)."""
    notas_com_unk = list(pd.unique(df_completo["Nota_leit"])) + [cfg["unk_token"]]
    le_nota = LabelEncoder().fit(notas_com_unk)
    le_target = LabelEncoder().fit(df_train["ANÁLISE"])
    return le_nota, le_target


def preparar_dados(df, cfg, vectorizer=None, encoders=None):
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
        X_pred_coment = df_pred["Comentleitura"].values
    else:
        X_pred_nota = None
        X_pred_coment = None

    X_train_nota = df_train["nota_enc"].values
    X_train_coment = df_train["Comentleitura"].values

    if vectorizer is None:
        vectorizer = TextVectorization(max_tokens=cfg["max_tokens_vocab"], output_sequence_length=cfg["seq_length"])
        vectorizer.adapt(X_train_coment)

    encoders = {"le_nota": le_nota, "le_target": le_target}
    return X_train_nota, X_train_coment, y_cat, y, encoders, vectorizer, X_pred_nota, X_pred_coment, df_pred


# ========================
# Modelo com texto
# ========================

def criar_modelo_texto(n_nota, n_classes, vectorizer, vocab_size):
    input_nota = Input(shape=(1,), name="nota_input")
    input_coment_text = Input(shape=(1,), dtype=tf.string, name="coment_input")

    emb_nota = Embedding(input_dim=n_nota, output_dim=8)(input_nota)
    emb_nota = Flatten()(emb_nota)

    x = vectorizer(input_coment_text)
    emb_coment = Embedding(input_dim=vocab_size, output_dim=32)(x)

    # Conv1D captura padrões locais de N-gramas (ex: "não recomendo"),
    # algo que a média pura de embeddings (GlobalAveragePooling sozinho) ignora.
    conv = Conv1D(filters=32, kernel_size=3, activation="relu", padding="same")(emb_coment)
    pool_max = GlobalMaxPooling1D()(conv)
    pool_avg = GlobalAveragePooling1D()(emb_coment)
    texto_repr = Concatenate()([pool_max, pool_avg])

    x = Concatenate()([emb_nota, texto_repr])
    x = Dense(64, activation="relu")(x)
    x = Dense(64, activation="relu")(x)
    output = Dense(n_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs=[input_nota, input_coment_text], outputs=output)
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
        X_train_nota, X_train_coment, y_cat, y_int, encoders, vectorizer,
        X_pred_nota, X_pred_coment, df_pred,
    ) = preparar_dados(df_completo, cfg)

    le_nota, le_target = encoders["le_nota"], encoders["le_target"]

    # Filtra classes com menos de 2 amostras (necessário para stratify)
    counts = Counter(y_int)
    classes_validas = {cls for cls, cnt in counts.items() if cnt >= 2}
    classes_descartadas = set(counts) - classes_validas
    if classes_descartadas:
        nomes_descartados = [le_target.classes_[c] for c in classes_descartadas]
        print(f"Aviso: classes com <2 amostras foram descartadas do treino: {nomes_descartados}")

    indices_validos = [i for i, label in enumerate(y_int) if label in classes_validas]
    X_train_nota = X_train_nota[indices_validos]
    X_train_coment = X_train_coment[indices_validos]
    y_cat = y_cat[indices_validos]
    y_int = y_int[indices_validos]

    X_nota_train, X_nota_val, X_coment_train, X_coment_val, y_train, y_val = train_test_split(
        X_train_nota, X_train_coment, y_cat, test_size=0.2, stratify=y_int, random_state=42
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
        print("Modelo salvo encontrado. Verificando compatibilidade com os dados atuais...")
        le_nota_salvo, le_target_salvo = carregar_encoders(cfg["encoders_path"])
        if len(le_nota_salvo.classes_) == n_nota and len(le_target_salvo.classes_) == n_classes:
            print("Compatível. Carregando modelo salvo (sem retreinar).")
            model = load_model(cfg["modelo_path"])
            le_nota, le_target = le_nota_salvo, le_target_salvo
            modelo_valido_encontrado = True
        else:
            print(
                "Modelo salvo é INCOMPATÍVEL com os dados atuais "
                f"(esperava {len(le_nota_salvo.classes_)} notas / {len(le_target_salvo.classes_)} classes, "
                f"dados atuais têm {n_nota} notas / {n_classes} classes). Retreinando do zero."
            )

    if not modelo_valido_encontrado:
        model = criar_modelo_texto(n_nota, n_classes, vectorizer, vocab_size=cfg["max_tokens_vocab"])

        early_stop = EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)
        checkpoint_cb = ModelCheckpoint(
            filepath=cfg["modelo_path"], save_best_only=True, monitor="val_loss", mode="min", verbose=1
        )

        print("Treinando modelo...")
        history = model.fit(
            {"nota_input": X_nota_train, "coment_input": X_coment_train},
            y_train,
            validation_data=({"nota_input": X_nota_val, "coment_input": X_coment_val}, y_val),
            epochs=cfg["epochs"],
            batch_size=cfg["batch_size"],
            verbose=1,
            callbacks=[early_stop, checkpoint_cb],
            class_weight=class_weights,
        )
        print("Treinamento finalizado e modelo salvo.")
        salvar_encoders(le_nota, le_target, cfg["encoders_path"])

        plt.figure()
        plt.plot(history.history["loss"], label="loss")
        plt.plot(history.history["val_loss"], label="val_loss")
        plt.legend()
        plt.title("Curva de Perda")
        plt.xlabel("Época")
        plt.ylabel("Loss")
        plt.savefig(cfg["grafico_loss_path"])
        print(f"Gráfico de perda salvo em {cfg['grafico_loss_path']}")

        y_val_pred_probs = model.predict({"nota_input": X_nota_val, "coment_input": X_coment_val})
        y_val_pred = y_val_pred_probs.argmax(axis=1)
        y_val_true = y_val.argmax(axis=1)
        target_names_filtrados = [le_target.classes_[i] for i in sorted(np.unique(y_int))]

        print("\nRelatório de Classificação (Validação):")
        print(classification_report(y_val_true, y_val_pred, target_names=target_names_filtrados))
        print(f"F1 macro: {f1_score(y_val_true, y_val_pred, average='macro'):.4f}")
        print(f"F1 weighted: {f1_score(y_val_true, y_val_pred, average='weighted'):.4f}")

    if X_pred_nota is not None and X_pred_coment is not None:
        pred_probs = model.predict({"nota_input": X_pred_nota, "coment_input": X_pred_coment})
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
