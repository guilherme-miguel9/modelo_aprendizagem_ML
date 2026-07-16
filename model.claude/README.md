# Pipeline de Classificação de Comentários (2 etapas)

## Visão geral

1. **Etapa 1** — lê o comentário e prevê qual das 20 classificações se aplica.
2. **Etapa 2** — verifica se o conteúdo do comentário realmente é coerente com a
   classificação aplicada. Se bater, marca como "OK". Se não bater, aplica uma
   das 7 siglas de inconsistência.

Modelo base: **BERTimbau** (`neuralmind/bert-base-portuguese-cased`), um BERT
pré-treinado em português, ajustado (fine-tuning) com os seus dados rotulados.

## Passo a passo

### 1. Preparar o ambiente (na máquina de casa, com GPU)

```bash
python -m venv venv
source venv/bin/activate  # no Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verifique se o PyTorch está enxergando sua GPU:
```python
import torch
print(torch.cuda.is_available())  # deve retornar True
```
Se retornar `False`, pode ser necessário instalar a versão do PyTorch com
suporte a CUDA compatível com sua placa de vídeo — veja https://pytorch.org
(selecione seu sistema operacional e versão do CUDA).

### 2. Preparar os dados

Exporte seu CSV com pelo menos estas colunas (nomes ajustáveis no `CONFIG`
de cada script):
- coluna com o texto do comentário
- coluna com a classificação aplicada (uma das 20)
- coluna com a sigla aplicada (uma das 7, ou um valor tipo "OK" quando não
  há inconsistência)

### 3. Treinar a Etapa 1

Ajuste o dicionário `CONFIG` no topo de `train_stage1_classificacao.py`
com os nomes reais das suas colunas, depois rode:

```bash
python train_stage1_classificacao.py
```

Isso gera a pasta `modelo_etapa1/` e o arquivo `label_encoder_etapa1.json`.

### 4. Treinar a Etapa 2

Mesma ideia, em `train_stage2_siglas.py`:

```bash
python train_stage2_siglas.py
```

Gera `modelo_etapa2/` e `label_encoder_etapa2.json`.

### 5. Levar para a máquina do trabalho (inferência, só CPU)

Copie para o PC do trabalho:
- pasta `modelo_etapa1/`
- pasta `modelo_etapa2/`
- `label_encoder_etapa1.json`
- `label_encoder_etapa2.json`
- `inferencia.py`
- `requirements.txt`

Instale as dependências e rode:
```bash
python inferencia.py
```

Ou importe a função em outro script/notebook:
```python
from inferencia import classificar_comentario
resultado = classificar_comentario("texto do comentário aqui")
print(resultado)
```

## Sobre a precisão

Nenhum modelo chega a 100% de acerto de forma confiável — mas com 1M+
exemplos rotulados, é realista buscar acurácia bem alta (frequentemente
90%+, dependendo de quão bem definidas/separáveis são as 20 classes e as
7 siglas).

Os scripts já retornam um **nível de confiança** por previsão
(`confianca_classificacao` e `confianca_sigla`) e uma flag
`revisar_manualmente` quando a confiança está abaixo de 0.6. Use isso
para criar uma fila de revisão humana apenas para os casos duvidosos —
essa é a forma prática de chegar perto de 100% de precisão no resultado
final (modelo + revisão nos casos incertos), em vez de exigir isso do
modelo sozinho.

## Próximos passos sugeridos

- Depois do primeiro treino, olhe a `classification_report` impressa no
  final — ela mostra precisão/recall por classe. Classes com poucos
  exemplos tendem a performar pior; pode ser necessário balancear os dados.
- Se alguma das 20 classes tiver uma definição textual clara (critério do
  que deve conter o comentário), incluir esse texto como contexto na
  Etapa 2 (além do nome da classe) tende a melhorar bastante a precisão
  da verificação de consistência.
- Ajuste `epochs`, `batch_size` e `learning_rate` no `CONFIG` se notar
  overfitting (métricas de treino muito melhores que as de validação) ou
  underfitting (ambas ruins).
