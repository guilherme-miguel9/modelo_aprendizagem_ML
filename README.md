# SmartRead ML & Routing — Auditoria de Leituras e Otimização de Rotas

Este projeto é uma solução inteligente integrada para distribuidoras de utilidades (água, gás, energia), dividida em dois grandes pilares:
1. **Auditoria de Comentários de Leitura**: Sistema híbrido (Regras de Negócio + Modelos de ML) para validar se as justificativas escritas pelos leituristas nos coletores de dados estão em conformidade com as regras operacionais.
2. **Otimização de Rotas (API de Roteamento)**: API desenvolvida em FastAPI que soluciona o problema do caixeiro-viajante (TSP) para otimizar as rotas diárias dos leituristas, gerando mapas interativos do trajeto ideal.

---

## 🚀 Funcionalidades

### 1. Auditoria e Validação de Comentários
Substitui ou complementa análises manuais demoradas através de um motor de validação baseado em regras e inteligência artificial que categoriza os comentários operacionais em:
* **C (Conforme)**: O comentário atende exatamente aos critérios exigidos pela nota de leitura.
* **SC (Sem Comentário)**: A nota exige justificativa, mas o campo foi enviado em branco.
* **UCE (Uso de Caractere Especial)**: Identifica caracteres especiais não permitidos (ex: `*`, `.`, `;`, `_`, `-`, `#`).
* **EE (Excesso de Espaço)**: Identifica espaçamentos incorretos (3 ou mais espaços consecutivos, ex: `'   '`).
* **FL (Falta a Leitura)**: Notas que necessitam de leitura operacional, mas esta não foi informada.
* **CFP (Comentário Fora do Padrão)**: Informações extras desnecessárias (como mais de 2 números no texto ou presença de letras em campos puramente numéricos).
* **CI (Comentário Incorreto)**: Conteúdo incompatível com a nota gerada.
* **NI (Nota Incorreta)**: A descrição do texto corresponde ao preenchimento de uma nota diferente.
* *Nota L121:* O robô ignora esta nota de campanha de forma inteligente, preservando análises manuais anteriores e deixando células vazias para auditoria manual.

### 2. Otimização de Rotas (FastAPI + TSP)
API que recebe uma lista de coordenadas geográficas e gera a rota de menor distância/tempo:
* **Algoritmo TSP**: Resolve o problema de otimização de rotas geográficas utilizando matrizes de distância Haversine e associação linear.
* **Visualização no Mapa**: Gera dinamicamente um arquivo HTML interativo com o mapa das rotas utilizando a biblioteca **Folium**.
* **Previsão de Tempo**: Estima tempo de tráfego com base em parâmetros de velocidade média configuráveis.

---

## 📁 Estrutura do Projeto

```
modelo_aprendizagem_ML/
├── data/
│   ├── raw/             # Planilhas/CSVs brutos de leitura
│   ├── processed/       # Bases pré-processadas para treino do modelo
│   └── new/             # Arquivos novos para predição/validação
├── models/
│   ├── api_route.py           # Endpoint FastAPI para otimização de rotas
│   ├── gerar_mapa.py          # Script gerador de mapas interativos Folium
│   ├── modelo_teste3.py       # Modelo RandomForest otimizado (scikit-learn)
│   ├── modelo_teste_neural.py # Rede Neural de classificação (TensorFlow/Keras)
│   └── rota_mapa.html         # Mapa gerado com a rota otimizada
├── src/
│   ├── validation_rules.py    # Motor de regras de negócio de validação
│   └── validar_comentarios.py # Script principal de validação de dados
├── requirements.txt           # Dependências do projeto
├── README.md                  # Este arquivo explicativo
└── melhor_modelo_texto.keras  # Modelo de rede neural treinado
```

---

## 🛠️ Tecnologias Utilizadas

* **Processamento de Dados**: `Pandas`, `Polars`, `Numpy`
* **Machine Learning**: `Scikit-Learn`, `TensorFlow/Keras`
* **API & Otimização**: `FastAPI`, `SciPy` (associação linear), `Folium` (mapas interativos)
* **Linguagem**: `Python 3.11+`

---

## 🔧 Como Instalar e Rodar

### Pré-requisitos
* Python 3.11 instalado.

### Instalação
1. Clone o repositório no seu workspace local.
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate # Linux/Mac
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Executar a Validação de Comentários (Robô)
O script de validação lê as tabelas e exporta os dados auditados para Excel:
* **Execução básica** (utiliza o arquivo de exemplo padrão em `data/new/`):
  ```bash
  python src/validar_comentarios.py
  ```
* **Executar com arquivos customizados**:
  ```bash
  python src/validar_comentarios.py --input seu_arquivo.csv --output saida.xlsx
  ```

### Executar a API de Roteamento
Para iniciar o servidor FastAPI localmente:
```bash
uvicorn models.api_route:app --reload
```
Acesse a documentação interativa da API em: `http://localhost:8000/docs`
