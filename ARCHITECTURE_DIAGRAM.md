# Architecture Diagram - modelo_aprendizagem_ML

## Overview
This project contains two main components:
1. **Machine Learning Pipeline** - Classification models for data analysis
2. **Route Optimization API** - FastAPI service for route calculation and visualization

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  data/raw/              data/processed/            data/new/               │
│  ┌─────────┐           ┌──────────────┐          ┌──────────────┐          │
│  │ CSV     │           │ mvc_000*_    │          │ mvc_0003_    │          │
│  │ Files   │ ────────▶ │ test.csv     │ ────────▶│ AGO_01.csv   │          │
│  └─────────┘           └──────────────┘          └──────────────┘          │
│                                                             │               │
│                                                             ▼               │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
┌─────────────────────────────────────────────────────────────┼───────────────┐
│                    ML PIPELINE MODELS                       │               │
├─────────────────────────────────────────────────────────────┼───────────────┤
│                                                             │               │
│  ┌──────────────────────────────────────────────────────┐   │               │
│  │  modelo_teste.py (RandomForest v1)                  │   │               │
│  │  - Loads CSV from data/new/                          │   │               │
│  │  - Polars data processing                            │   │               │
│  │  - Categorical encoding (Comentleitura, Nota_leit)   │   │               │
│  │  - RandomForestClassifier (100 estimators)           │   │               │
│  │  - Predicts ANÁLISE column                           │   │               │
│  │  - Output: avaliados_pelo_modelo.xlsx               │   │               │
│  └──────────────────────────────────────────────────────┘   │               │
│                                                             │               │
│  ┌──────────────────────────────────────────────────────┐   │               │
│  │  modelo_teste2.py (RandomForest v2)                  │   │               │
│  │  - Loads from data/processed/ (training)             │   │               │
│  │  - Loads from data/new/ (target)                      │   │               │
│  │  - Similar encoding pipeline                          │   │               │
│  │  - Preserves existing ANÁLISE values                  │   │               │
│  │  - Output: avaliado_01_ago.xlsx                      │   │               │
│  └──────────────────────────────────────────────────────┘   │               │
│                                                             │               │
│  ┌──────────────────────────────────────────────────────┐   │               │
│  │  modelo_teste3.py (RandomForest v3 - Optimized)       │   │               │
│  │  - Modular functions for data loading/prep           │   │               │
│  │  - Enhanced RandomForest params:                     │   │               │
│  │    * n_estimators=200, max_depth=10                  │   │               │
│  │    * class_weight='balanced'                         │   │               │
│  │  - Excludes "AGO" files from training                │   │               │
│  │  - Output: avaliado_01_ago.xlsx                      │   │               │
│  └──────────────────────────────────────────────────────┘   │               │
│                                                             │               │
│  ┌──────────────────────────────────────────────────────┐   │               │
│  │  modelo_teste_neural.py (Neural Network)              │   │               │
│  │  - Text vectorization (TextVectorization)            │   │               │
│  │  - Embedding layers for text (Comentleitura)         │   │               │
│  │  - Embedding for categorical (Nota_leit)              │   │               │
│  │  - Architecture:                                      │   │               │
│  │    Input(nota) → Embedding → Flatten                 │   │               │
│  │    Input(text) → Vectorizer → Embedding → Pool       │   │               │
│  │    Concatenate → Dense(64) → Dense(64) → Softmax     │   │               │
│  │  - Class weighting for imbalanced data               │   │               │
│  │  - Early stopping & model checkpointing              │   │               │
│  │  - Saves: melhor_modelo_texto.keras                 │   │               │
│  │  - Output: avaliado_01_ago_nn_embedding.xlsx        │   │               │
│  └──────────────────────────────────────────────────────┘   │               │
│                                                             │               │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
┌─────────────────────────────────────────────────────────────┼───────────────┐
│                    ROUTE OPTIMIZATION API                    │               │
├─────────────────────────────────────────────────────────────┼───────────────┤
│                                                             │               │
│  ┌──────────────────────────────────────────────────────┐   │               │
│  │  api_route.py (FastAPI)                              │   │               │
│  │                                                       │   │               │
│  │  POST /rota                                          │   │               │
│  │  ┌──────────────────────────────────────────────┐   │   │               │
│  │  │ Input: List of (lat, lon) coordinates        │   │   │               │
│  │  │                                              │   │   │               │
│  │  │ Process:                                    │   │   │               │
│  │  │ 1. Convert to radians                       │   │   │               │
│  │  │ 2. Calculate haversine distance matrix      │   │   │               │
│  │  │ 3. Linear sum assignment for TSP            │   │   │               │
│  │  │ 4. Build optimal route                       │   │   │               │
│  │  │ 5. Calculate total distance & time           │   │   │               │
│  │  │                                              │   │   │               │
│  │  │ Output:                                      │   │   │               │
│  │  │ - Route order (indices)                     │   │   │               │
│  │  │ - Ordered coordinates                        │   │   │               │
│  │  │ - Total distance (km)                        │   │   │               │
│  │  │ - Estimated times per segment               │   │   │               │
│  │  └──────────────────────────────────────────────┘   │   │               │
│  │                              │                         │   │               │
│  │                              ▼                         │   │               │
│  │  ┌──────────────────────────────────────────────┐   │   │               │
│  │  │ gerar_mapa.py                                 │   │   │               │
│  │  │ - Folium map generation                       │   │   │               │
│  │  │ - Markers for each point                      │   │   │               │
│  │  │ - Polyline for route visualization             │   │   │               │
│  │  │ - Saves: rota_mapa.html                       │   │   │               │
│  │  └──────────────────────────────────────────────┘   │   │               │
│  │                                                       │   │               │
│  │  GET /mapa                                           │   │               │
│  │  └──▶ Returns rota_mapa.html                         │   │               │
│  │                                                       │   │               │
│  └──────────────────────────────────────────────────────┘   │               │
│                                                             │               │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
┌─────────────────────────────────────────────────────────────┼───────────────┐
│                    OUTPUT FILES                                │               │
├─────────────────────────────────────────────────────────────┼───────────────┤
│                                                             │               │
│  Excel Outputs:                                             │               │
│  - avaliados_pelo_modelo.xlsx                               │               │
│  - avaliado_01_ago.xlsx                                      │               │
│  - avaliado_01_ago_nn_embedding.xlsx                         │               │
│                                                             │               │
│  Model Files:                                                │               │
│  - melhor_modelo_texto.keras                                │               │
│  - encoders.json                                            │               │
│                                                             │               │
│  Visualization:                                             │               │
│  - rota_mapa.html                                            │               │
│  - curva_perda.png                                          │               │
│                                                             │               │
└─────────────────────────────────────────────────────────────┴───────────────┘
```

---

## Data Flow (ML Pipeline)

```
CSV Data (data/new/, data/processed/)
    │
    ▼
Polars/Pandas Loading
    │
    ▼
Column Normalization (remove spaces, newlines, dots)
    │
    ▼
Feature Engineering
    │
    ├──► Comentleitura (text) ──► Categorical Encoding ──► Integer
    │
    └──► Nota_leit (text) ──────► Categorical Encoding ──► Integer
    │
    ▼
Train/Test Split
    │
    ├──► Training Data (ANÁLISE not null)
    │       │
    │       ▼
    │   Model Training
    │       │
    │       ├──► RandomForest (sklearn)
    │       │    └──► 100-200 trees, balanced classes
    │       │
    │       └──► Neural Network (TensorFlow)
    │            └──► Embeddings + Dense layers
    │
    └──► Prediction Data (ANÁLISE null)
            │
            ▼
        Model Prediction
            │
            ▼
        Fill ANÁLISE column
            │
            ▼
        Excel Output
```

---

## Data Flow (Route API)

```
Client Request (POST /rota)
    │
    ▼
JSON: {"pontos": [(lat1, lon1), (lat2, lon2), ...]}
    │
    ▼
Convert to Radians
    │
    ▼
Haversine Distance Matrix (km)
    │
    ▼
Linear Sum Assignment (TSP solver)
    │
    ▼
Build Optimal Route
    │
    ▼
Calculate:
    - Total distance
    - Segment times (60 km/h default)
    │
    ├─► Generate Folium Map (gerar_mapa.py)
    │       │
    │       └──► Save rota_mapa.html
    │
    └─► Return JSON Response
            │
            ├──► route: [0, 2, 1, 3, ...]
            ├──► ordem: [(lat, lon), ...]
            ├──► distancia_total_km: 123.45
            └──► tempo_estimados_horas: [1.2, 0.8, ...]
```

---

## Key Dependencies

### ML Pipeline
- **polars** - Fast data processing
- **pandas** - Data manipulation
- **scikit-learn** - RandomForest, LabelEncoder, metrics
- **tensorflow/keras** - Neural network, embeddings, callbacks
- **numpy** - Numerical operations

### Route API
- **fastapi** - Web framework
- **pydantic** - Data validation
- **scipy** - Linear sum assignment (TSP)
- **folium** - Map visualization
- **sklearn** - Haversine distances

---

## Model Comparison

| Model | Type | Features | Architecture | Output |
|-------|------|----------|--------------|--------|
| modelo_teste.py | RandomForest | Comentleitura, Nota_leit | 100 trees | avaliados_pelo_modelo.xlsx |
| modelo_teste2.py | RandomForest | Comentleitura, Nota_leit | 100 trees | avaliado_01_ago.xlsx |
| modelo_teste3.py | RandomForest | Comentleitura, Nota_leit | 200 trees, optimized | avaliado_01_ago.xlsx |
| modelo_teste_neural.py | Neural Network | Comentleitura (text), Nota_leit | Embeddings + Dense | avaliado_01_ago_nn_embedding.xlsx |

---

## File Structure Summary

```
modelo_aprendizagem_ML/
├── data/
│   ├── raw/           # Original CSV files
│   ├── processed/     # Processed training data (mvc_000*_test.csv)
│   └── new/           # New data for prediction (mvc_0003_AGO_01.csv)
├── models/
│   ├── api_route.py           # FastAPI route optimization
│   ├── gerar_mapa.py          # Folium map generation
│   ├── modelo_teste.py        # RandomForest v1
│   ├── modelo_teste2.py       # RandomForest v2
│   ├── modelo_teste3.py       # RandomForest v3 (optimized)
│   ├── modelo_teste_neural.py # Neural network with embeddings
│   └── rota_mapa.html         # Generated route visualization
├── src/                    # Empty skeleton files (planned structure)
│   ├── config.py
│   ├── evaluate.py
│   ├── predict.py
│   ├── preprocess.py
│   └── train_model.py
├── main.py                 # Empty (planned entry point)
├── requirements.txt        # Dependencies
├── README.md              # Project description
├── melhor_modelo_texto.keras  # Saved neural network model
├── encoders.json          # Saved label encoders
└── curva_perda.png        # Training loss curve
```

---

## Notes

- The `src/` directory contains empty skeleton files suggesting a planned modular structure that hasn't been implemented yet
- All current ML models are standalone scripts in `models/` directory
- The route optimization API is completely separate from the ML pipeline
- ML models predict the "ANÁLISE" column based on reading comments and notes
- The neural network model uses text embeddings for better text feature representation
- All RandomForest models use categorical encoding for text features
