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
        # Tokens e abreviações permitidas que podem aparecer nos comentários
        self.tokens_permitidos = ['NR DI', 'NR RE', 'NR IM', 'SELO', 'ZELO', 'S', 'R']
        # Notas onde o comentário não é obrigatório ou o token pode vir sozinho
        self.notas_sem_comentario = ["T161", "L131", "P191", "T171", "L121"]
    
    def validar_comentario(self, nota: str, comentario: str) -> Optional[str]:
        """
        Valida um comentário baseado na nota de leitura.
        """
        if nota == "L121":
            return None
            
        if pd.isna(comentario) or str(comentario).strip() == "":
            return self._validar_comentario_vazio(nota)
        
        comentario = str(comentario).strip()
        
        # Verificar caracteres especiais (pegar todos os caracteres especiais de todos os comentários)
        if self._tem_caracteres_especiais(comentario):
            return "UCE"
        
        # Verificar excesso de espaços (3 ou mais)
        if self._tem_excesso_espacos(comentario):
            return "EE"
            
        # Verificar se as notas T181 ou R111 possuem 03 (+ até 6 dígitos), configurando CFP
        if nota in ["T181", "R111"]:
            if re.search(r'\b03\d{0,6}\b', comentario):
                return "CFP"
                
        # Verificar se o comentário possui apenas os tokens permitidos (S | SELO | ZELO | NR DI | NR RE | R | NR IM)
        if self._e_apenas_token_permitido(comentario):
            if nota in self.notas_sem_comentario:
                return "C"
            # Se não for de nota sem comentário (ou seja, notas que exigem comentário), não pode vir só:
            # Continua para a validação específica da nota abaixo para verificar falta de dados
        
        # Obter regra para a nota
        regra = VALIDATION_RULES.get(nota)
        if not regra:
            return "C"
        
        # Validar baseado no tipo de conteúdo requerido
        return self._validar_conteudo_requerido(nota, comentario, regra)
    
    def _validar_comentario_vazio(self, nota: str) -> str:
        """Valida quando o comentário está vazio"""
        if nota in self.notas_sem_comentario:
            return "C"
        return "SC"
    
    def _tem_caracteres_especiais(self, comentario: str) -> bool:
        """Verifica se o comentário contém caracteres especiais"""
        # UCE: pegar todos os caracteres especiais de todos os comentários (*, ., ;, _, -, #, /, @, !, ?, etc.)
        return bool(re.search(r'[^\w\s]', comentario, re.UNICODE))
    
    def _tem_excesso_espacos(self, comentario: str) -> bool:
        """Verifica se há excesso de espaços (3 ou mais consecutivos)"""
        return '   ' in comentario
        
    def _e_apenas_token_permitido(self, comentario: str) -> bool:
        """Verifica se o comentário é apenas composto pelos tokens permitidos (sem números ou outros textos)"""
        temp = comentario.upper()
        for token in sorted(self.tokens_permitidos, key=len, reverse=True):
            temp = re.sub(r'\b' + token + r'\b', '', temp)
        return temp.strip() == ""
        
    def _contem_letras_nao_permitidas(self, comentario: str) -> bool:
        """Verifica se há letras no comentário ignorando os tokens permitidos (S, SELO, ZELO, NR DI, NR RE, R, NR IM)"""
        temp = comentario.upper()
        for token in sorted(self.tokens_permitidos, key=len, reverse=True):
            temp = re.sub(r'\b' + token + r'\b', '', temp)
        return bool(re.search(r'[A-ZÁ-Ú]', temp))
    
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
        """Valida formato: MEDIDOR + LEITURA (dois valores numéricos ou 103/55 + até 6 dígitos)"""
        numeros = re.findall(r'\d+', comentario)
        if len(numeros) == 0:
            return "NI"  # Não tem números, comentário não faz sentido com a nota solicitada
            
        if self._contem_letras_nao_permitidas(comentario):
            return "CFP"
            
        # Se tem apenas 1 número, verificar se é o padrão junto 103/55 + até 6 dígitos
        if len(numeros) == 1:
            if re.match(r'^(103|55)\d{1,6}$', numeros[0]):
                return "C"
            return "FL"  # Falta leitura
            
        tem_prefixo = any(re.match(r'^(103|55)\d{0,6}$', num) for num in numeros)
        limite_numeros = 3 if tem_prefixo else 2
        
        if len(numeros) > limite_numeros:
            return "CFP"
            
        return "C"
    
    def _validar_medidor_leitura_funcao(self, comentario: str, funcoes_validas: list) -> str:
        """Valida formato: MEDIDOR + LEITURA (apenas para funções 01 e 02)"""
        tem_funcao_valida = any(func in comentario for func in funcoes_validas)
        if not tem_funcao_valida:
            return "NI"
        return self._validar_medidor_leitura(comentario)
    
    def _validar_formato_poste(self, comentario: str) -> str:
        """Valida formato: M000000 (1 letra M e 6 números) ou X seguido de número"""
        if not re.search(r'\d', comentario):
            return "NI"
            
        if self._contem_letras_nao_permitidas(comentario):
            coment_sem_poste = re.sub(r'[MX]\d+', '', comentario, flags=re.IGNORECASE)
            if self._contem_letras_nao_permitidas(coment_sem_poste):
                return "CFP"
                
        padrao_m = r'M\d{6}'
        padrao_x = r'X\d+'
        
        if re.search(padrao_m, comentario, re.IGNORECASE) or re.search(padrao_x, comentario, re.IGNORECASE):
            return "C"
            
        return "CI"
    
    def _validar_texto_condizente(self, comentario: str) -> str:
        """Valida se o texto é condizente com a nota (texto descritivo)"""
        if len(comentario) < 1:
            return "CI"
        return "C"
    
    def _validar_campanha(self, comentario: str, nota: str) -> str:
        """Valida informações de campanha"""
        return "C"
    
    def _validar_medidor_sem_leitura(self, comentario: str) -> str:
        """Valida: UM OU DOIS MEDIDORES (SEM LEITURA)"""
        numeros = re.findall(r'\d+', comentario)
        if len(numeros) == 0:
            return "NI"
            
        if self._contem_letras_nao_permitidas(comentario):
            return "CFP"
            
        tem_prefixo = any(re.match(r'^(103|55)\d{0,6}$', num) for num in numeros)
        limite_numeros = 3 if tem_prefixo else 2
        
        if len(numeros) > limite_numeros:
            return "CFP"
            
        return "C"
    
    def _validar_apenas_funcao(self, comentario: str) -> str:
        """Valida: APENAS FUNÇÃO"""
        if re.match(r'^\d{2}$', comentario.strip()):
            return "C"
        return "CFP"
    
    def _validar_funcao_leitura(self, comentario: str, funcao_invalida: str) -> str:
        """Valida: FUNÇÃO + LEITURA (função 03 já validada acima em T181)"""
        numeros = re.findall(r'\d+', comentario)
        if len(numeros) == 0:
            return "NI"
            
        if self._contem_letras_nao_permitidas(comentario):
            return "CFP"
            
        if len(numeros) == 1:
            if re.match(r'^(103|55)\d{1,6}$', numeros[0]):
                return "C"
            if len(numeros[0]) <= 4 and not re.match(r'^(103|55)', numeros[0]):
                return "CI"
            return "FL"
            
        tem_prefixo = any(re.match(r'^(103|55)\d{0,6}$', num) for num in numeros)
        limite_numeros = 3 if tem_prefixo else 2
        
        if len(numeros) > limite_numeros:
            return "CFP"
            
        return "C"


def aplicar_validacao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica validação em um DataFrame inteiro.
    """
    validator = CommentValidator()
    
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
        
        if pd.notna(row.get('ANÁLISE')):
            resultados.append(row['ANÁLISE'])
        else:
            analise = validator.validar_comentario(nota, comentario)
            resultados.append(analise)
    
    df_copy = df.copy()
    df_copy['ANÁLISE'] = resultados
    return df_copy


if __name__ == "__main__":
    validator = CommentValidator()
    
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
        ("T181", "03 12345", "CFP"), # T181 com 03 -> CFP
        ("R111", "0312345", "CFP"),  # R111 com 03 + dígitos -> CFP
        ("B111", "103123456", "C"),  # 103 + até 6 dígitos em B111 -> C
        ("P111", "12345 6789 SELO", "C"), # Token permitido junto com leitura -> C
        ("L131", "SELO", "C"), # Token permitido sozinho em nota sem comentário obrigatório -> C
        ("P111", "SELO", "NI"), # Token permitido sozinho em nota com comentário obrigatório -> NI
        ("T181", "103 15040.", "UCE"), # Caractere especial -> UCE
        ("P111", "cliente nao estava", "NI") # Comentário não faz sentido com a nota -> NI
    ]
    
    print("Testes de validacao:")
    for nota, comentario, esperado in test_cases:
        resultado = validator.validar_comentario(nota, comentario)
        status = "[OK]" if resultado == esperado else "[FAIL]"
        print(f"{status} Nota: {nota}, Comentario: '{comentario}' -> {resultado} (esperado: {esperado})")

