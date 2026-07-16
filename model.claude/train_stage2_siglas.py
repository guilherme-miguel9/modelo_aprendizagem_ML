"""
ETAPA 2 - Verifica se o comentário bate com a classificação aplicada.
Se bater -> classe "OK" (sem inconsistência).
Se não bater -> uma das 7 siglas de inconsistência.

Ideia central: o modelo recebe o COMENTÁRIO + a CLASSIFICAÇÃO que foi aplicada
(como texto de contexto), e aprende a dizer se aquilo é coerente ou não.
Isso dá ao modelo a "regra" que ele precisa checar, em vez de adivinhar sozinho.

Como usar:
1. Ajuste CONFIG com os nomes reais das colunas do seu CSV.
   Sua coluna de sigla deve conter os 7 códigos OU um valor tipo "OK"/"SEM_INCONSISTENCIA"
   para os casos em que bateu. Se seu CSV não tiver esse valor "OK" explícito,
   ajuste a função carregar_dados() para criá-lo (ver comentário no código).
2. Rode em máquina com GPU.
3. Modelo final salvo em ./modelo_etapa2/

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
    "csv_path": "dados_rotulados.csv",
    "csv_separator": ",",
    "coluna_comentario": "comentario",
    "coluna_classe": "classificacao",     # a classe aplicada (uma das 20)
    "coluna_sigla": "sigla",              # a sigla (uma das 7) ou "OK" quando bate
    "valor_quando_ok": "OK",              # como está escrito no seu CSV quando não há inconsistência
    "modelo_base": "neuralmind/bert-base-portuguese-cased",
    "max_length": 300,
    "output_dir": "./modelo_etapa2",
    "epochs": 3,
    "batch_size": 16,
    "learning_rate": 2e-5,
    "test_size": 0.15,
    "seed": 42,
}


def carregar_dados(cfg):
    df = pd.read_csv(cfg["csv_path"], sep=cfg["csv_separator"])
    df = df[[cfg["coluna_comentario"], cfg["coluna_classe"], cfg["coluna_sigla"]]].dropna(
        subset=[cfg["coluna_comentario"], cfg["coluna_classe"]]
    )
    df.columns = ["texto", "classe", "sigla"]
    df["texto"] = df["texto"].astype(str)

    # Se não houver valor "OK" explícito no seu CSV (ex: sigla vem vazia quando bate),
    # descomente a linha abaixo para preencher automaticamente:
    # df["sigla"] = df["sigla"].fillna(cfg["valor_quando_ok"])

    # Combina comentário + classe aplicada em um único texto de entrada.
    # Isso dá ao modelo o contexto de "qual regra checar".
    df["texto_entrada"] = "Classificação aplicada: " + df["classe"] + " | Comentário: " + df["texto"]
    return df


class ConsistenciaDataset(torch.utils.data.Dataset):
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
    print(df["sigla"].value_counts())

    le = LabelEncoder()
    df["label_id"] = le.fit_transform(df["sigla"])
    with open("label_encoder_etapa2.json", "w", encoding="utf-8") as f:
        json.dump({str(i): c for i, c in enumerate(le.classes_)}, f, ensure_ascii=False, indent=2)
    num_classes = len(le.classes_)
    print(f"Número de classes detectadas (siglas + OK): {num_classes}")

    train_df, val_df = train_test_split(
        df, test_size=cfg["test_size"], stratify=df["label_id"], random_state=cfg["seed"]
    )

    tokenizer = AutoTokenizer.from_pretrained(cfg["modelo_base"])
    train_ds = ConsistenciaDataset(train_df["texto_entrada"], train_df["label_id"], tokenizer, cfg["max_length"])
    val_ds = ConsistenciaDataset(val_df["texto_entrada"], val_df["label_id"], tokenizer, cfg["max_length"])

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
        fp16=torch.cuda.is_available(),
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
    print("Concluído. Copie a pasta do modelo + label_encoder_etapa2.json para usar em outra máquina.")


if __name__ == "__main__":
    main()
