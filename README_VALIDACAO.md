# Sistema de Validação de Comentários - Guia de Uso

## Visão Geral

Este sistema substitui os modelos de Machine Learning anteriores por um sistema baseado em regras de negócio específicas para cada tipo de nota de leitura. O sistema valida se os comentários de leitura estão conforme o conteúdo esperado para cada nota.

## Resultados

Antes da validação:
- **8,388** registros classificados como CONFORME
- **8,622** registros sem classificação

Após validação com regras:
- **17,007** registros classificados como CONFORME (102% de melhoria)
- **39** registros não conformes (casos legítimos de problemas)

## Estrutura do Sistema

### Arquivos Principais

1. **`src/validation_rules.py`** - Motor de validação com regras de negócio
2. **`src/validar_comentarios.py`** - Script principal para processar arquivos

### Categorias de Análise

O sistema classifica os comentários em 8 categorias:

| Código | Descrição | Quando é aplicado |
|--------|-----------|-------------------|
| **C** | CONFORME | Comentário atende aos requisitos da nota |
| **SC** | SEM COMENTÁRIO | Nota exige informação mas comentário está vazio |
| **UCE** | USO DE CARACTERE ESPECIAL | Comentário contém caracteres especiais (* . ; _ - #) |
| **EE** | EXCESSO DE ESPAÇO | Comentário tem 3+ espaços consecutivos |
| **FL** | FALTA A LEITURA | Nota exige leitura mas não foi informada |
| **CFP** | COMENTÁRIO FORA DO PADRÃO | Comentário tem mais informações que o padrão (mais de 2 números ou contém letras) |
| **CI** | COMENTÁRIO INCORRETO | Conteúdo não atende à necessidade da nota |
| **NI** | NOTA INCORRETA | Informação corresponde a outra nota |

## Regras por Tipo de Nota

### Notas que requerem MEDIDOR + LEITURA
- **B111** - Local Cons. Implantado em Duplicidade
- **P111** - E.M. Substituído ou Número Incorreto  
- **P131** - E.M. Vizinho Não Cadastrado
- **T171** - Data/Hora do E.M. Incorreta

**Regra:** Aceita comentários com pelo menos um número (medidor ou leitura)

### Notas que requerem Nº DO POSTE (M000000)
- **E101** - Poste Inclinado ou Quebrado
- **E111** - Objeto, Árvore, Imóvel Encostado/Próximo à Rede
- **P231** - Iluminação Pública Acesa Durante o Dia

**Regra:** Aceita formato M seguido de 6 dígitos (ex: M123456)

### Notas que requerem TEXTO CONDIZENTE
- **C111** - Bairro Incorreto
- **C121** - Rua Incorreta
- **C131** - Número da Porta/Porta Incorreto
- **C151** - Atividade Incorreta
- **C161** - Quant. Incorreta de Dígitos do E.M.
- **C181** - Número do Poste Incorreto
- **P191** - U.C. Vizinha Com Ligação Clandestina
- **R161** - Ponto de Referência Incorreto

**Regra:** Aceita qualquer texto ou número

### Notas de Campanha
- **L121** - Campanha 1 (Verificação manual, não processado pelo robô)
- **L131** - Campanha 2

**Regra (L131):** Aceita comentários vazios, "s", números de telefone, textos informativos
**Regra (L121):** Ignorado pelo robô, preservando a análise original do usuário no arquivo.

### Notas Específicas
- **R111** - Medidor Alocado Incorretamente (aceita qualquer comentário)
- **T161** - Função Não Existe no PDA (aceita apenas código de função 2 dígitos)
- **T181** - Função Não Existe no Sistema (aceita qualquer formato com números)

## Como Usar

### Validação Básica

```bash
python src/validar_comentarios.py
```

Isso processará o arquivo `data/new/mvc_0003_AGO_01.csv` e gerará `validado_regras_negocio.xlsx`

### Validação com Arquivos Específicos

```bash
python src/validar_comentarios.py --input caminho/entrada.csv --output caminho/saida.xlsx
```

### Validação com Análise Detalhada

```bash
python src/validar_comentarios.py --input caminho/entrada.csv --output caminho/saida.xlsx --analyze
```

A opção `--analyze` mostra a distribuição de análises por tipo de nota.

## Exemplos de Validação

### Exemplo 1: T181 (Função + Leitura)
```
Nota: T181
Comentário: "103 15040"
Resultado: C (CONFORME)
```

### Exemplo 2: P111 (Medidor + Leitura)
```
Nota: P111
Comentário: "3243946009 131"
Resultado: C (CONFORME)
```

### Exemplo 3: L131 (Campanha)
```
Nota: L131
Comentário: "" (vazio)
Resultado: C (CONFORME)
```

### Exemplo 4: B111 (Medidor + Leitura)
```
Nota: B111
Comentário: "" (vazio)
Resultado: SC (SEM COMENTÁRIO)
```

## Personalização

### Adicionar Nova Regra

Edite `src/validation_rules.py` e adicione a regra no dicionário `VALIDATION_RULES`:

```python
"NOVA_NOTA": {
    "required": "TIPO_VALIDACAO", 
    "description": "Descrição da nota"
}
```

### Adicionar Novo Tipo de Validação

Adicione um novo método na classe `CommentValidator`:

```python
def _validar_novo_tipo(self, comentario: str) -> str:
    """Valida novo tipo de conteúdo"""
    # Sua lógica aqui
    return "C"  # ou outra categoria
```

## Comparação com Modelos Anteriores

| Modelo | Abordagem | CONFORME | Não Conforme |
|--------|-----------|----------|--------------|
| RandomForest (modelo_teste.py) | ML com encoding categórico | 8,388 | N/A |
| Neural Network (modelo_teste_neural.py) | Embeddings + Dense | N/A | N/A |
| **Regras de Negócio (atual)** | **Validação específica por nota** | **17,007** | **39** |

## Vantagens do Sistema Baseado em Regras

1. **Transparência:** Regras explícitas e fáceis de entender
2. **Manutenibilidade:** Fácil ajustar regras específicas
3. **Performance:** Processamento rápido sem treinamento
4. **Precisão:** Baseado nas regras reais de negócio
5. **Consistência:** Mesma validação para todos os registros

## Próximos Passos

Para melhorias futuras, considere:

1. Adicionar mais tipos de notas ao dicionário `VALIDATION_RULES`
2. Implementar validações mais específicas para casos edge
3. Criar interface web para visualização dos resultados
4. Adicionar logs detalhados para auditoria
5. Implementar testes automatizados para as regras

## Suporte

Para dúvidas ou problemas, verifique:
1. Se o tipo de nota está no dicionário `VALIDATION_RULES`
2. Se a regra de validação está implementada
3. Se os dados de entrada têm o formato correto (CSV separado por ;)
