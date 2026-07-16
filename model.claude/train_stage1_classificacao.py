"""
ETAPA 1 - Classificação principal do comentário em uma das 20 classes.

Como usar:
1. Ajuste o dicionário CONFIG abaixo com os nomes reais das colunas do seu CSV.
2. Rode este script em uma máquina COM GPU (o script detecta automaticamente
   se há GPU disponível via torch.cuda.is_available()).
3. Ao final, o modelo treinado fica salvo em ./modelo_etapa1/
   -> copie essa pasta para a máquina de trabalho para usar em inferência.

Requisitos: pip install -r requirements.txt
"""

import json
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.preprocessing import LabelEncoder
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

# =========================================================
# CONFIGURAÇÃO — AJUSTE AQUI CONFORME SEU CSV
# =========================================================
CONFIG = {
    "csv_path": "dados_rotulados.csv",       # caminho do seu CSV
    "csv_separator": ",",                     # ou ";" se for CSV exportado do Excel BR
    "coluna_comentario": "comentario",        # nome da coluna com o texto do comentário
    "coluna_classe": "classificacao",         # nome da coluna com a classe (1 das 20)
    "modelo_base": "neuralmind/bert-base-portuguese-cased",
    "max_length": 256,                        # tamanho máximo do comentário em tokens
    "output_dir": "./modelo_etapa1",
    "epochs": 3,
    "batch_size": 16,                         # reduza para 8 se faltar memória de GPU
    "learning_rate": 2e-5,
    "test_size": 0.15,                        # % dos dados para validação
    "seed": 42,
}


def carregar_dados(cfg):
    df = pd.read_csv(cfg["csv_path"], sep=cfg["csv_separator"])
    df = df[[cfg["coluna_comentario"], cfg["coluna_classe"]]].dropna()
    df.columns = ["texto", "classe"]
    df["texto"] = df["texto"].astype(str)
    return df


class ComentarioDataset(torch.utils.data.Dataset):
    def __init__(self, textos, labels, tokenizer, max_length):
        self.encodings = tokenizer(
            list(textos),
            truncation=True,
            padding=True,
            max_length=max_length,
        )
        self.labels = list(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
        "f1_weighted": f1_score(labels, preds, average="weighted"),
    }


def main():
    cfg = CONFIG
    print(f"GPU disponível: {torch.cuda.is_available()}")

    print("Carregando dados...")
    df = carregar_dados(cfg)
    print(f"Total de exemplos: {len(df)}")
    print(df["classe"].value_counts())

    # Codifica as 20 classes em números (0 a 19)
    le = LabelEncoder()
    df["label_id"] = le.fit_transform(df["classe"])
    with open("label_encoder_etapa1.json", "w", encoding="utf-8") as f:
        json.dump({str(i): c for i, c in enumerate(le.classes_)}, f, ensure_ascii=False, indent=2)
    num_classes = len(le.classes_)
    print(f"Número de classes detectadas: {num_classes}")

    # Split treino/validação, estratificado para manter proporção das classes
    train_df, val_df = train_test_split(
        df, test_size=cfg["test_size"], stratify=df["label_id"], random_state=cfg["seed"]
    )

    tokenizer = AutoTokenizer.from_pretrained(cfg["modelo_base"])
    train_ds = ComentarioDataset(train_df["texto"], train_df["label_id"], tokenizer, cfg["max_length"])
    val_ds = ComentarioDataset(val_df["texto"], val_df["label_id"], tokenizer, cfg["max_length"])

    model = AutoModelForSequenceClassification.from_pretrained(
        cfg["modelo_base"], num_labels=num_classes
    )

    training_args = TrainingArguments(
        output_dir=cfg["output_dir"],
        num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch_size"],
        per_device_eval_batch_size=cfg["batch_size"],
        learning_rate=cfg["learning_rate"],
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        logging_steps=50,
        fp16=torch.cuda.is_available(),  # acelera o treino se tiver GPU
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )

    print("Iniciando treinamento...")
    trainer.train()

    print("\nAvaliação final no conjunto de validação:")
    preds = trainer.predict(val_ds)
    y_pred = np.argmax(preds.predictions, axis=-1)
    print(classification_report(val_df["label_id"], y_pred, target_names=le.classes_))

    print(f"\nSalvando modelo final em {cfg['output_dir']}...")
    trainer.save_model(cfg["output_dir"])
    tokenizer.save_pretrained(cfg["output_dir"])
    print("Concluído. Copie a pasta do modelo + label_encoder_etapa1.json para usar em outra máquina.")


if __name__ == "__main__":
    main()
