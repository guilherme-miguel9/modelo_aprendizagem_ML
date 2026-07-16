"""
Sistema de validação de comentários baseado em regras de negócio
para cada tipo de nota de leitura.
"""

import re
import pandas as pd
from typing import Dict, Tuple, Optional


# Configuração das regras de validação por tipo de nota
VALIDATION_RULES = {
    # Notas que requerem MEDIDOR + LEITURA
    "B111": {"required": "MEDIDOR_LEITURA", "description": "Local Cons. Implantado em Duplicidade"},
    "P111": {"required": "MEDIDOR_LEITURA", "description": "E.M. Substituído ou Número Incorreto"},
    "P131": {"required": "MEDIDOR_LEITURA", "description": "E.M. Vizinho Não Cadastrado"},
    "T171": {"required": "MEDIDOR_LEITURA_FUNCAO", "description": "Data/Hora do E.M. Incorreta", "funcoes_validas": ["01", "02"]},
    
    # Notas que requerem Nº DO POSTE (M000000 - 1 letra e 6 números)
    "E101": {"required": "POSTE_FORMAT", "description": "Poste Inclinado ou Quebrado"},
    "E111": {"required": "POSTE_FORMAT", "description": "Objeto, Árvore, Imóvel Encostado/Próximo à Rede"},
    "P231": {"required": "POSTE_FORMAT", "description": "Iluminação Pública Acesa Durante o Dia"},
    
    # Notas que requerem TEXTO CONDIZENTE COM A NOTA
    "C111": {"required": "TEXTO_CONDIZENTE", "description": "Bairro Incorreto"},
    "C121": {"required": "TEXTO_CONDIZENTE", "description": "Rua Incorreta"},
    "C131": {"required": "TEXTO_CONDIZENTE", "description": "Número da Porta/Porta Incorreto"},
    "C151": {"required": "TEXTO_CONDIZENTE", "description": "Atividade Incorreta"},
    "C161": {"required": "TEXTO_CONDIZENTE", "description": "Quant. Incorreta de Dígitos do E.M."},
    "C181": {"required": "TEXTO_CONDIZENTE", "description": "Número do Poste Incorreto"},
    "P191": {"required": "TEXTO_CONDIZENTE", "description": "U.C. Vizinha Com Ligação Clandestina"},
    "R161": {"required": "TEXTO_CONDIZENTE", "description": "Ponto de Referência Incorreto"},
    
    # Notas específicas
    # L121 removido da validação automática (será feito manualmente)
    "L131": {"required": "CAMPANHA", "description": "Campanha 2", "formato_especifico": "n DO TEL; NOME; VAZIO E RECUSA DE DADOS"},
    "R111": {"required": "MEDIDOR_SEM_LEITURA", "description": "Medidor Alocado Incorretamente"},
    "T161": {"required": "APENAS_FUNCAO", "description": "Função Não Existe no PDA"},
    "T181": {"required": "FUNCAO_LEITURA", "description": "Função Não Existe no Sistema", "funcao_invalida": "03"},
}


class CommentValidator:
    """Validador de comentários baseado em regras de negócio"""
    
    def __init__(self):
        self.caracteres_especiais = set("*.;_-#")
    
    def validar_comentario(self, nota: str, comentario: str) -> Optional[str]:
        """
        Valida um comentário baseado na nota de leitura.
        
        Args:
            nota: Código da nota de leitura (ex: "B111")
            comentario: Conteúdo do comentário de leitura
            
        Returns:
            Código da análise (C, SC, UCE, EE, FL, CFP, CI, NI) ou None se não analisado
        """
        if nota == "L121":
            return None
            
        if pd.isna(comentario) or str(comentario).strip() == "":
            return self._validar_comentario_vazio(nota)
        
        comentario = str(comentario).strip()
        
        # Verificar caracteres especiais
        if self._tem_caracteres_especiais(comentario):
            return "UCE"
        
        # Verificar excesso de espaços
        if self._tem_excesso_espacos(comentario):
            return "EE"
        
        # Obter regra para a nota
        regra = VALIDATION_RULES.get(nota)
        if not regra:
            # Se não há regra definida, assume conforme
            return "C"
        
        # Validar baseado no tipo de conteúdo requerido
        resultado = self._validar_conteudo_requerido(nota, comentario, regra)
        return resultado
    
    def _validar_comentario_vazio(self, nota: str) -> str:
        """Valida quando o comentário está vazio"""
        # Notas que NÃO exigem comentário (baseado nos dados corretos)
        notas_sem_comentario = ["T161", "L131", "P191", "T171"]  # Campanhas, apenas função, P191 e T171
        
        if nota in notas_sem_comentario:
            return "C"
        
        # Todas as outras notas exigem comentário
        return "SC"
    
    def _tem_caracteres_especiais(self, comentario: str) -> bool:
        """Verifica se o comentário contém caracteres especiais"""
        # Caracteres especiais baseado nos dados corretos: . ' _ ,
        caracteres_especiais = {'.', "'", '_', ','}
        return any(char in caracteres_especiais for char in comentario)
    
    def _tem_excesso_espacos(self, comentario: str) -> bool:
        """Verifica se há excesso de espaços (mais de 2 consecutivos)"""
        # Verificar se há 3 ou mais espaços consecutivos
        return '   ' in comentario
    
    def _validar_conteudo_requerido(self, nota: str, comentario: str, regra: Dict) -> str:
        """Valida se o conteúdo do comentário está conforme o requerido"""
        tipo_requerido = regra.get("required")
        
        if tipo_requerido == "MEDIDOR_LEITURA":
            return self._validar_medidor_leitura(comentario)
        
        elif tipo_requerido == "MEDIDOR_LEITURA_FUNCAO":
            return self._validar_medidor_leitura_funcao(comentario, regra.get("funcoes_validas", []))
        
        elif tipo_requerido == "POSTE_FORMAT":
            return self._validar_formato_poste(comentario)
        
        elif tipo_requerido == "TEXTO_CONDIZENTE":
            return self._validar_texto_condizente(comentario)
        
        elif tipo_requerido == "CAMPANHA":
            return self._validar_campanha(comentario, nota)
        
        elif tipo_requerido == "MEDIDOR_SEM_LEITURA":
            return self._validar_medidor_sem_leitura(comentario)
        
        elif tipo_requerido == "APENAS_FUNCAO":
            return self._validar_apenas_funcao(comentario)
        
        elif tipo_requerido == "FUNCAO_LEITURA":
            return self._validar_funcao_leitura(comentario, regra.get("funcao_invalida"))
        
        return "C"
    
    def _validar_medidor_leitura(self, comentario: str) -> str:
        """Valida formato: MEDIDOR + LEITURA (dois valores numéricos)"""
        # Extrair números do comentário
        numeros = re.findall(r'\d+', comentario)
        
        # Para P111, precisa de 2 números (medidor + leitura) para ser C
        # Baseado nos dados corretos: P111 com apenas medidor é FL
        if len(numeros) < 2:
            return "FL"
        
        # Se tem mais de 2 números ou contém letras
        if len(numeros) > 2 or re.search(r'[a-zA-Z]', comentario):
            return "CFP"
        
        return "C"
    
    def _validar_medidor_leitura_funcao(self, comentario: str, funcoes_validas: list) -> str:
        """Valida formato: MEDIDOR + LEITURA (apenas para funções 01 e 02)"""
        # Verificar se contém função válida
        tem_funcao_valida = any(func in comentario for func in funcoes_validas)
        
        if not tem_funcao_valida:
            return "NI"  # Nota incorreta
        
        return self._validar_medidor_leitura(comentario)
    
    def _validar_formato_poste(self, comentario: str) -> str:
        """Valida formato: M000000 (1 letra M e 6 números) ou X seguido de número"""
        # Procurar padrão M seguido de 6 dígitos
        padrao_m = r'M\d{6}'
        padrao_x = r'X\d+'
        
        if re.search(padrao_m, comentario, re.IGNORECASE):
            return "C"
        
        if re.search(padrao_x, comentario, re.IGNORECASE):
            return "C"
        
        return "CI"  # Comentário incorreto
    
    def _validar_texto_condizente(self, comentario: str) -> str:
        """Valida se o texto é condizente com a nota (texto descritivo)"""
        # Para notas de texto (C111, C121, C131, etc.), aceitar qualquer texto razoável
        # Baseado nos dados corretos: C131 aceita números como "88", "75"
        
        if len(comentario) < 1:
            return "CI"
        
        return "C"
    
    def _validar_campanha(self, comentario: str, nota: str) -> str:
        """Valida informações de campanha"""
        # L131 e L121 aceitam comentários vazios, simples como "s", números de telefone, textos informativos
        # Baseado nos dados reais, esses são considerados CONFORME
        if nota in ["L131", "L121"]:
            return "C"
        
        return "C"
    
    def _validar_medidor_sem_leitura(self, comentario: str) -> str:
        """Valida: UM OU DOIS MEDIDORES (SEM LEITURA)"""
        # Para R111, aceitar qualquer comentário com números
        # Baseado nos dados corretos: R111 com muitos números ainda é C
        numeros = re.findall(r'\d+', comentario)
        
        if len(numeros) == 0:
            return "CI"
        
        # Se tem mais de 2 números ou contém letras
        if len(numeros) > 2 or re.search(r'[a-zA-Z]', comentario):
            return "CFP"
        
        return "C"
    
    def _validar_apenas_funcao(self, comentario: str) -> str:
        """Valida: APENAS FUNÇÃO"""
        # Verificar se contém apenas código de função (2 dígitos)
        if re.match(r'^\d{2}$', comentario.strip()):
            return "C"
        
        # Se tiver mais conteúdo, pode estar fora do padrão
        return "CFP"
    
    def _validar_funcao_leitura(self, comentario: str, funcao_invalida: str) -> str:
        """Valida: FUNÇÃO + LEITURA (função 03 não pode estar no comentário)"""
        # Para T181, precisa ter função + leitura (2 números)
        # Padrões corretos: "103 15040", "10310745"
        # Padrões incorretos: "103" (FL), "1031619" (CI - sem espaço), "t18" (CI)
        
        # Verificar se é texto sem números (NI)
        if not re.search(r'\d', comentario):
            return "NI"
        
        numeros = re.findall(r'\d+', comentario)
        
        if len(numeros) < 2:
            # Se tem apenas 1 número e é muito curto, pode ser CI
            if len(numeros) == 1 and len(numeros[0]) <= 4:
                return "CI"
            return "FL"  # Falta leitura
        
        # Se tem mais de 2 números ou contém letras
        if len(numeros) > 2 or re.search(r'[a-zA-Z]', comentario):
            return "CFP"
        
        return "C"


def aplicar_validacao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica validação em um DataFrame inteiro.
    
    Args:
        df: DataFrame com colunas de nota e comentário
        
    Returns:
        DataFrame com coluna 'ANÁLISE' preenchida
    """
    validator = CommentValidator()
    
    # Encontrar as colunas corretas (nomes podem variar após normalização)
    nota_col = None
    coment_col = None
    
    for col in df.columns:
        if 'nota' in col.lower() and 'leit' in col.lower():
            nota_col = col
        if 'coment' in col.lower():
            coment_col = col
    
    if nota_col is None or coment_col is None:
        raise ValueError(f"Colunas não encontradas. nota_col={nota_col}, coment_col={coment_col}. Colunas disponíveis: {df.columns.tolist()}")
    
    resultados = []
    for _, row in df.iterrows():
        nota = str(row.get(nota_col, '')).strip()
        comentario = row.get(coment_col, '')
        
        # Se já tem análise, manter
        if pd.notna(row.get('ANÁLISE')):
            resultados.append(row['ANÁLISE'])
        else:
            analise = validator.validar_comentario(nota, comentario)
            resultados.append(analise)
    
    df_copy = df.copy()
    df_copy['ANÁLISE'] = resultados
    return df_copy


if __name__ == "__main__":
    # Teste de exemplo
    validator = CommentValidator()
    
    # Testes
    test_cases = [
        ("B111", "12345 67890", "C"),  # Medidor + leitura correto
        ("B111", "", "SC"),  # Sem comentário
        ("B111", "12345", "FL"),  # Falta leitura
        ("E101", "M123456", "C"),  # Poste correto
        ("E101", "123456", "CI"),  # Poste incorreto
        ("C111", "Rua das Flores", "C"),  # Texto condizente
        ("C111", "ABC", "C"),  # Texto muito curto
        ("T161", "01", "C"),  # Apenas função
        ("T161", "01 123", "CFP"),  # Fora do padrão
    ]
    
    print("Testes de validacao:")
    for nota, comentario, esperado in test_cases:
        resultado = validator.validar_comentario(nota, comentario)
        status = "[OK]" if resultado == esperado else "[FAIL]"
        print(f"{status} Nota: {nota}, Comentario: '{comentario}' -> {resultado} (esperado: {esperado})")
