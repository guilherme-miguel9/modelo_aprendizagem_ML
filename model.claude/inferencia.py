"""
INFERÊNCIA - roda o pipeline completo (Etapa 1 + Etapa 2) em um comentário novo.
Feito para funcionar em CPU (não precisa de GPU aqui).

Como usar:
1. Copie as pastas modelo_etapa1/ e modelo_etapa2/ (geradas nos scripts de treino)
   + os arquivos label_encoder_etapa1.json e label_encoder_etapa2.json
   para a mesma pasta deste script.
2. pip install -r requirements.txt (na máquina de trabalho também)
3. Ajuste a lista `comentarios_teste` lá embaixo, ou importe `classificar_comentario()`
   em outro script/notebook.
"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

CAMINHO_MODELO_ETAPA1 = "./modelo_etapa1"
CAMINHO_MODELO_ETAPA2 = "./modelo_etapa2"

print("Carregando modelos (isso pode levar alguns segundos)...")

tokenizer1 = AutoTokenizer.from_pretrained(CAMINHO_MODELO_ETAPA1)
model1 = AutoModelForSequenceClassification.from_pretrained(CAMINHO_MODELO_ETAPA1)
model1.eval()

tokenizer2 = AutoTokenizer.from_pretrained(CAMINHO_MODELO_ETAPA2)
model2 = AutoModelForSequenceClassification.from_pretrained(CAMINHO_MODELO_ETAPA2)
model2.eval()

with open("label_encoder_etapa1.json", encoding="utf-8") as f:
    labels_etapa1 = json.load(f)  # {"0": "classe_a", "1": "classe_b", ...}

with open("label_encoder_etapa2.json", encoding="utf-8") as f:
    labels_etapa2 = json.load(f)


def classificar_comentario(texto, limiar_confianca=0.6):
    """
    Retorna um dicionário com a classificação prevista, a sigla (ou OK),
    e os níveis de confiança de cada etapa — útil para saber quando
    revisar manualmente um caso.
    """
    # ---- Etapa 1: classificação principal ----
    inputs1 = tokenizer1(texto, truncation=True, max_length=256, return_tensors="pt")
    with torch.no_grad():
        logits1 = model1(**inputs1).logits
    probs1 = torch.softmax(logits1, dim=-1)[0]
    pred_id1 = int(torch.argmax(probs1))
    classe_prevista = labels_etapa1[str(pred_id1)]
    confianca1 = float(probs1[pred_id1])

    # ---- Etapa 2: verificação de consistência ----
    texto_entrada2 = f"Classificação aplicada: {classe_prevista} | Comentário: {texto}"
    inputs2 = tokenizer2(texto_entrada2, truncation=True, max_length=300, return_tensors="pt")
    with torch.no_grad():
        logits2 = model2(**inputs2).logits
    probs2 = torch.softmax(logits2, dim=-1)[0]
    pred_id2 = int(torch.argmax(probs2))
    sigla_prevista = labels_etapa2[str(pred_id2)]
    confianca2 = float(probs2[pred_id2])

    revisar_manualmente = confianca1 < limiar_confianca or confianca2 < limiar_confianca

    return {
        "comentario": texto,
        "classificacao": classe_prevista,
        "confianca_classificacao": round(confianca1, 3),
        "sigla": sigla_prevista,
        "confianca_sigla": round(confianca2, 3),
        "revisar_manualmente": revisar_manualmente,
    }


if __name__ == "__main__":
    comentarios_teste = [
        "Coloque aqui um comentário real de exemplo para testar.",
    ]
    for c in comentarios_teste:
        resultado = classificar_comentario(c)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
