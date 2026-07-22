import os
import sys
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

# Adicionar o diretório raiz e o subdiretório src ao PATH de forma segura para PyInstaller e dev
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)
src_dir = os.path.join(base_dir, 'src')
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

# Importação resiliente de regras de validação para modo CLI e modo PyInstaller (.exe)
aplicar_validacao_func = None
try:
    from src.validation_rules import aplicar_validacao
    aplicar_validacao_func = aplicar_validacao
except ImportError:
    try:
        from validation_rules import aplicar_validacao
        aplicar_validacao_func = aplicar_validacao
    except ImportError as err:
        print(f"Aviso ao importar validation_rules: {err}")

try:
    from src.validar_comentarios import carregar_dados, normalizar_colunas
except ImportError:
    try:
        from validar_comentarios import carregar_dados, normalizar_colunas
    except ImportError:
        pass

# Configuração de tema escuro com paleta Azul Escuro Navy (Dark Navy Blue)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RaisedGlassCard(ctk.CTkFrame):
    """Card com elevação e profundidade visual"""
    def __init__(self, master, corner_radius=18, fg_color="#181A24", border_color="#282C3E", border_width=1, **kwargs):
        super().__init__(
            master=master,
            corner_radius=corner_radius,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            **kwargs
        )


class MetricBadge(ctk.CTkFrame):
    """Badge indicador de status e métricas operacionais"""
    def __init__(self, master, label, value, color="#3B82F6", **kwargs):
        super().__init__(
            master=master,
            corner_radius=14,
            fg_color="#14161F",
            border_color="#252838",
            border_width=1,
            **kwargs
        )
        self.label_lbl = ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#8E93B0"
        )
        self.label_lbl.pack(pady=(10, 2), padx=12)
        
        self.value_lbl = ctk.CTkLabel(
            self, text=str(value), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=color
        )
        self.value_lbl.pack(pady=(0, 10), padx=12)

    def update_value(self, value):
        self.value_lbl.configure(text=str(value))


class AuditorComentariosApp(ctk.CTk):
    """Painel principal de Auditoria de Registros Operacionais - Paleta Azul Escuro Navy & Sidebar Funcional"""
    def __init__(self):
        super().__init__()

        # Configuração da Janela Principal
        self.title("Auditoria de Registros Operacionais — Sistema de Validação")
        self.geometry("1080x760")
        self.minsize(940, 660)
        self.configure(fg_color="#0F111A")

        # Variáveis de Controle e Estado
        self.selected_file_path = ctk.StringVar(value="")
        self.sheet_name_var = ctk.StringVar(value="Aud_Coment_Geral")
        self.output_file_path = ctk.StringVar(value="")
        self.is_processing = False
        self.current_tab = "visao_geral"

        # Histórico de sessão
        self.last_run_time = "Nenhuma auditoria executada nesta sessão"
        self.last_total_rows = 0
        self.last_elapsed_secs = 0.0

        # Grid principal: 2 colunas (Sidebar lateral esquerdo + Painel Central multifuncional)
        self.grid_columnconfigure(0, weight=0, minsize=240)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_container()
        self._switch_view("visao_geral")

    def _build_sidebar(self):
        """Painel lateral esquerdo com 3 abas funcionais em Azul Escuro Navy"""
        sidebar_frame = ctk.CTkFrame(self, fg_color="#14161F", corner_radius=0, border_color="#222636", border_width=1)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(6, weight=1)

        # Logo e Identidade
        logo_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(26, 20), sticky="ew")

        icon_box = ctk.CTkLabel(
            logo_frame,
            text="⬡",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color="#3B82F6",
            width=42,
            height=42,
            fg_color="#1E2A4A",
            corner_radius=12
        )
        icon_box.grid(row=0, column=0, padx=(0, 12))

        title_lbl = ctk.CTkLabel(
            logo_frame,
            text="Auditoria de\nRegistros Operacionais",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#FFFFFF",
            justify="left"
        )
        title_lbl.grid(row=0, column=1, sticky="w")

        # Divisor
        ctk.CTkFrame(sidebar_frame, height=1, fg_color="#222636").grid(row=1, column=0, sticky="ew", padx=16, pady=6)

        # Botões do Sidebar Funcional (Sem aba Regras & Tokens)
        self.nav_buttons = {}
        nav_configs = [
            ("visao_geral", "⚡ Visão Geral", 2),
            ("planilhas", "📁 Planilha & Pastas", 3),
            ("historico", "📊 Histórico Auditoria", 4),
        ]

        for tab_id, label, row_idx in nav_configs:
            btn = ctk.CTkButton(
                sidebar_frame,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="transparent",
                text_color="#8E93B0",
                hover_color="#1E2436",
                anchor="w",
                height=44,
                corner_radius=12,
                command=lambda tid=tab_id: self._switch_view(tid)
            )
            btn.grid(row=row_idx, column=0, padx=16, pady=5, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # Card de informações operacionais na parte inferior do sidebar
        info_card = RaisedGlassCard(sidebar_frame, corner_radius=14, fg_color="#11131C", border_color="#222636")
        info_card.grid(row=7, column=0, padx=16, pady=24, sticky="ew")

        ctk.CTkLabel(
            info_card,
            text="Auditoria Operacional v2.1",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#D8DBE8"
        ).pack(pady=(12, 4), padx=14, anchor="w")

        ctk.CTkLabel(
            info_card,
            text="Paleta Azul Escuro Navy,\nregras de negócio dinâmicas\ne checagem em background.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#6C728E",
            justify="left"
        ).pack(pady=(0, 12), padx=14, anchor="w")

    def _build_main_container(self):
        """Container central que abriga os painéis de visualização (abas)"""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Construir as views
        self.views = {}
        self.views["visao_geral"] = self._create_visao_geral_view()
        self.views["planilhas"] = self._create_planilhas_view()
        self.views["historico"] = self._create_historico_view()

    def _switch_view(self, tab_id):
        """Alterna a visualização ativa entre os botões do sidebar"""
        self.current_tab = tab_id
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                # Botão ativo em Azul Escuro Navy (#1E3A8A / #1D4ED8)
                btn.configure(fg_color="#1E3A8A", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#8E93B0")

        for tid, view in self.views.items():
            if tid == tab_id:
                view.grid(row=0, column=0, padx=28, pady=20, sticky="nsew")
            else:
                view.grid_forget()

        # Se mudou para histórico, atualizar informações
        if tab_id == "historico":
            self._update_historico_view()

    # =========================================================================
    # VIEW 1: VISÃO GERAL (Principal)
    # =========================================================================
    def _create_visao_geral_view(self):
        view = ctk.CTkScrollableFrame(
            self.main_container, fg_color="transparent", scrollbar_button_color="#222636", scrollbar_button_hover_color="#33394E"
        )
        view.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        header_frame = ctk.CTkFrame(view, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(10, 18), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Auditoria Operacional de Comentários",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_frame,
            text="Selecione a planilha Excel ou CSV para processar todas as regras operacionais instantaneamente.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8E93B0"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # CARD 1: SELEÇÃO DA PLANILHA
        file_card = RaisedGlassCard(view, corner_radius=18, fg_color="#181A24", border_color="#282C3E")
        file_card.grid(row=1, column=0, pady=(0, 16), sticky="ew")
        file_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            file_card,
            text="Arquivo de Auditoria (.xlsx, .xlsm, .csv)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#D8DBE8"
        ).grid(row=0, column=0, padx=22, pady=(16, 10), sticky="w")

        file_input = ctk.CTkFrame(file_card, fg_color="transparent")
        file_input.grid(row=1, column=0, padx=22, pady=(0, 14), sticky="ew")
        file_input.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            file_input,
            textvariable=self.selected_file_path,
            placeholder_text="Nenhum arquivo carregado... Clique em 'Selecionar Planilha'",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=46,
            corner_radius=12,
            fg_color="#0F111A",
            border_color="#25293A",
            text_color="#FFFFFF"
        )
        self.file_entry.grid(row=0, column=0, padx=(0, 12), sticky="ew")

        select_btn = ctk.CTkButton(
            file_input,
            text="📁 Selecionar Planilha",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=46,
            width=175,
            corner_radius=12,
            fg_color="#1D4ED8",
            hover_color="#1E40AF",
            text_color="#FFFFFF",
            command=self._select_file
        )
        select_btn.grid(row=0, column=1)

        # Opções de Aba
        options_box = ctk.CTkFrame(file_card, fg_color="#12141D", corner_radius=12, border_color="#222636", border_width=1)
        options_box.grid(row=2, column=0, padx=22, pady=(0, 16), sticky="ew")
        options_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            options_box,
            text="Nome da Aba Excel:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#A0A5C0"
        ).grid(row=0, column=0, padx=(16, 12), pady=14, sticky="w")

        self.sheet_entry = ctk.CTkEntry(
            options_box,
            textvariable=self.sheet_name_var,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36,
            corner_radius=8,
            fg_color="#181A24",
            border_color="#282C3E"
        )
        self.sheet_entry.grid(row=0, column=1, padx=(0, 16), pady=14, sticky="ew")

        # CARD 2: STATUS E PROGRESSO (Azul Escuro Navy)
        self.progress_card = RaisedGlassCard(view, corner_radius=18, fg_color="#181A24", border_color="#282C3E")
        self.progress_card.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self.progress_card.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Pronto para iniciar auditoria operacional",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#A0A5C0"
        )
        self.status_lbl.grid(row=0, column=0, padx=22, pady=(16, 10), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_card,
            height=10,
            corner_radius=5,
            fg_color="#0F111A",
            progress_color="#3B82F6"
        )
        self.progress_bar.grid(row=1, column=0, padx=22, pady=(0, 12), sticky="ew")
        self.progress_bar.set(0)

        self.progress_detail_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Aguardando seleção de planilha para análise de regras operacionais",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#6C728E"
        )
        self.progress_detail_lbl.grid(row=2, column=0, padx=22, pady=(0, 16), sticky="w")

        # CARD 3: DASHBOARD DE MÉTRICAS (GRID)
        self.results_card = RaisedGlassCard(view, corner_radius=18, fg_color="#181A24", border_color="#282C3E")
        self.results_card.grid(row=3, column=0, pady=(0, 18), sticky="ew")
        self.results_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            self.results_card,
            text="Indicadores e Distribuição da Auditoria",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#D8DBE8"
        ).grid(row=0, column=0, columnspan=4, padx=22, pady=(16, 12), sticky="w")

        self.badges = {}
        metric_configs = [
            ("Conforme (C)", "C", "#2ECC71", 1, 0),
            ("Fora Padrão (CFP)", "CFP", "#E74C3C", 1, 1),
            ("Sem Coment. (SC)", "SC", "#F39C12", 1, 2),
            ("Falta Leitura (FL)", "FL", "#9B59B6", 1, 3),
            ("Nota Incorreta (NI)", "NI", "#FF5C4D", 2, 0),
            ("Espaço Exc. (EE)", "EE", "#3498DB", 2, 1),
            ("Coment. Inc. (CI)", "CI", "#F1C40F", 2, 2),
            ("Caractere Esp. (UCE)", "UCE", "#E67E22", 2, 3),
        ]

        for label, key, color, row, col in metric_configs:
            badge = MetricBadge(self.results_card, label=label, value="-", color=color)
            badge.grid(row=row, column=col, padx=10, pady=8, sticky="nsew")
            self.badges[key] = badge

        ctk.CTkLabel(self.results_card, text="", height=6).grid(row=3, column=0, columnspan=4)

        # RODAPÉ DE AÇÃO
        footer_frame = ctk.CTkFrame(view, fg_color="transparent")
        footer_frame.grid(row=4, column=0, pady=(4, 20), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        self.action_btn = ctk.CTkButton(
            footer_frame,
            text="▶ Executar Auditoria e Gerar Planilha",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=52,
            corner_radius=14,
            fg_color="#1D4ED8",
            hover_color="#1E40AF",
            text_color="#FFFFFF",
            command=self._start_validation_thread
        )
        self.action_btn.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        self.open_excel_btn = ctk.CTkButton(
            footer_frame,
            text="📁 Abrir Planilha Validada",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=52,
            width=210,
            corner_radius=14,
            fg_color="#1E2436",
            hover_color="#2A324A",
            text_color="#FFFFFF",
            state="disabled",
            command=self._open_generated_file
        )
        self.open_excel_btn.grid(row=0, column=1)

        return view

    # =========================================================================
    # VIEW 2: PLANILHAS & PASTAS
    # =========================================================================
    def _create_planilhas_view(self):
        view = ctk.CTkScrollableFrame(
            self.main_container, fg_color="transparent", scrollbar_button_color="#222636", scrollbar_button_hover_color="#33394E"
        )
        view.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            view,
            text="Gestão de Planilhas e Diretórios de Saída",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF"
        ).grid(row=0, column=0, pady=(10, 18), sticky="w")

        card = RaisedGlassCard(view, corner_radius=18, fg_color="#181A24", border_color="#282C3E")
        card.grid(row=1, column=0, pady=10, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Detalhes dos Arquivos de Origem e Validado",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#D8DBE8"
        ).grid(row=0, column=0, padx=22, pady=(20, 12), sticky="w")

        self.planilha_info_lbl = ctk.CTkLabel(
            card,
            text="Nenhum arquivo selecionado no momento.\nVá em 'Visão Geral' e selecione sua planilha de auditoria.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8E93B0",
            justify="left"
        )
        self.planilha_info_lbl.grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")

        # Botão para abrir pasta onde o arquivo está ou será salvo
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.grid(row=2, column=0, padx=22, pady=(0, 20), sticky="w")

        ctk.CTkButton(
            btn_box,
            text="📂 Abrir Pasta de Destino no Windows Explorer",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=44,
            corner_radius=12,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            command=self._open_target_folder
        ).pack(side="left", padx=(0, 12))

        return view

    # =========================================================================
    # VIEW 3: HISTÓRICO DA AUDITORIA
    # =========================================================================
    def _create_historico_view(self):
        view = ctk.CTkScrollableFrame(
            self.main_container, fg_color="transparent", scrollbar_button_color="#222636", scrollbar_button_hover_color="#33394E"
        )
        view.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            view,
            text="Histórico e Resumo de Performance da Sessão",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF"
        ).grid(row=0, column=0, pady=(10, 18), sticky="w")

        card = RaisedGlassCard(view, corner_radius=18, fg_color="#181A24", border_color="#282C3E")
        card.grid(row=1, column=0, pady=10, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        self.historico_txt_lbl = ctk.CTkLabel(
            card,
            text="Nenhuma execução realizada até o momento nesta sessão aberta do aplicativo.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#8E93B0",
            justify="left"
        )
        self.historico_txt_lbl.grid(row=0, column=0, padx=22, pady=24, sticky="w")

        return view

    def _update_historico_view(self):
        if self.last_total_rows > 0:
            msg = (
                f"🕒 Última Execução Realizada em: {self.last_run_time}\n\n"
                f"📊 Total de Linhas Analisadas: {self.last_total_rows:,} comentários\n"
                f"⚡ Tempo Total de Processamento: {self.last_elapsed_secs} segundos\n"
                f"📁 Planilha de Saída Gravada: {self.output_file_path.get()}"
            )
            self.historico_txt_lbl.configure(text=msg, text_color="#D8DBE8")

    # =========================================================================
    # AÇÕES DO SISTEMA E PROCESSAMENTO EM THREAD
    # =========================================================================
    def _select_file(self):
        if self.is_processing:
            return
        file_path = filedialog.askopenfilename(
            title="Selecione a Planilha de Auditoria",
            filetypes=[
                ("Arquivos Excel (.xlsx, .xlsm, .xls)", "*.xlsx *.xlsm *.xls"),
                ("Arquivos CSV (.csv)", "*.csv"),
                ("Todos os Arquivos", "*.*")
            ]
        )
        if file_path:
            self.selected_file_path.set(file_path)
            base_dir = os.path.dirname(file_path)
            file_name, _ = os.path.splitext(os.path.basename(file_path))
            out_path = os.path.join(base_dir, f"{file_name}_VALIDADO.xlsx")
            self.output_file_path.set(out_path)
            self.status_lbl.configure(text=f"Planilha selecionada: {os.path.basename(file_path)}", text_color="#2ECC71")
            self.progress_detail_lbl.configure(text=f"Destino de saída: {out_path}")
            
            # Atualizar view da aba planilhas
            info_text = (
                f"📄 Arquivo Origem:\n{file_path}\n\n"
                f"📑 Aba Excel Selecionada:\n{self.sheet_name_var.get()}\n\n"
                f"💾 Arquivo Validado a Gerar:\n{out_path}"
            )
            if hasattr(self, 'planilha_info_lbl'):
                self.planilha_info_lbl.configure(text=info_text, text_color="#D8DBE8")

    def _open_target_folder(self):
        file_path = self.selected_file_path.get()
        if file_path and os.path.exists(file_path):
            folder = os.path.dirname(file_path)
            os.startfile(folder)
        else:
            folder = os.path.abspath(".")
            os.startfile(folder)

    def _start_validation_thread(self):
        if self.is_processing:
            return
        file_path = self.selected_file_path.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Atenção", "Por favor, selecione um arquivo válido antes de executar a análise.")
            return

        self.is_processing = True
        self.action_btn.configure(state="disabled", text="⏳ Processando Regras Operacionais...")
        self.open_excel_btn.configure(state="disabled")
        self.progress_bar.set(0.1)
        self.status_lbl.configure(text="Carregando planilha e normalizando colunas...", text_color="#3B82F6")
        self.progress_detail_lbl.configure(text="Lendo estrutura de dados na memória do sistema...")

        threading.Thread(target=self._run_validation_pipeline, args=(file_path,), daemon=True).start()

    def _run_validation_pipeline(self, file_path):
        start_time = time.time()
        try:
            aba = self.sheet_name_var.get().strip() or None
            
            self.progress_bar.set(0.25)
            self.status_lbl.configure(text="Carregando dados da planilha...")
            
            try:
                from src.validar_comentarios import carregar_dados, normalizar_colunas
                df = carregar_dados(file_path, aba)
            except Exception:
                if file_path.endswith('.xlsx') or file_path.endswith('.xls') or file_path.endswith('.xlsm'):
                    xls = pd.ExcelFile(file_path)
                    aba_use = aba if aba and aba in xls.sheet_names else xls.sheet_names[0]
                    df = pd.read_excel(file_path, sheet_name=aba_use, dtype={"Nº_Serie": str})
                else:
                    df = pd.read_csv(file_path, sep=';', dtype={"Nº_Serie": str})
                df.columns = [str(col).strip().replace('\n', '').replace('\r', '').replace('.', '').replace(' ', '_') for col in df.columns]

            self.progress_bar.set(0.50)
            self.status_lbl.configure(text=f"Analisando {len(df):,} comentários com Regras Operacionais...")
            self.progress_detail_lbl.configure(text="Verificando prefixos S, notas no texto, limites e formatações de poste...")

            analise_col = None
            for col in df.columns:
                if 'analise' in col.lower() or 'análise' in col.lower():
                    analise_col = col
                    break
            
            nota_col = None
            for col in df.columns:
                if 'nota' in col.lower() and 'leit' in col.lower():
                    nota_col = col
                    break
                    
            if analise_col is None:
                df['ANÁLISE'] = None
                analise_col = 'ANÁLISE'
            else:
                df = df.rename(columns={analise_col: 'ANÁLISE'})
                analise_col = 'ANÁLISE'
                if nota_col is not None:
                    df.loc[df[nota_col].astype(str).str.strip() != 'L121', 'ANÁLISE'] = None
                else:
                    df['ANÁLISE'] = None

            # Aplicar validação por regras de forma resiliente e à prova de variações de assinatura
            func_val = aplicar_validacao_func
            if func_val is None:
                try:
                    from src.validation_rules import aplicar_validacao as func_val
                except ImportError:
                    from validation_rules import aplicar_validacao as func_val

            try:
                df = func_val(df, coluna_comentario='Coment_leitura', coluna_nota='Nota_leit', coluna_analise='ANÁLISE')
            except TypeError:
                df = func_val(df)

            self.progress_bar.set(0.75)
            self.status_lbl.configure(text="Gravando planilha Excel validada na mesma pasta...")
            self.progress_detail_lbl.configure(text="Salvando todas as classificações e indicadores gerados...")

            out_path = self.output_file_path.get()
            df.to_excel(out_path, index=False)

            elapsed = round(time.time() - start_time, 1)
            self.progress_bar.set(1.0)
            self.status_lbl.configure(text=f"✔ Auditoria Concluída com Sucesso em {elapsed}s!", text_color="#2ECC71")
            self.progress_detail_lbl.configure(text=f"Planilha gravada perfeitamente em: {out_path}")

            dist = df['ANÁLISE'].value_counts().to_dict()
            for key in self.badges:
                val = dist.get(key, 0)
                self.badges[key].update_value(f"{val:,}".replace(',', '.'))

            # Salvar estatísticas no histórico
            self.last_run_time = time.strftime("%d/%m/%Y às %H:%M:%S")
            self.last_total_rows = len(df)
            self.last_elapsed_secs = elapsed

            self.after(10, self._on_validation_success)

        except Exception as e:
            err_msg = str(e)
            self.after(10, lambda: self._on_validation_error(err_msg))

    def _on_validation_success(self):
        self.is_processing = False
        self.action_btn.configure(state="normal", text="▶ Executar Auditoria e Gerar Planilha")
        self.open_excel_btn.configure(state="normal", fg_color="#2ECC71", hover_color="#27AE60")
        messagebox.showinfo("Sucesso", "A auditoria da planilha foi concluída com êxito!\n\nArquivo validado gravado na pasta original.")

    def _on_validation_error(self, error_message):
        self.is_processing = False
        self.action_btn.configure(state="normal", text="▶ Executar Auditoria e Gerar Planilha")
        self.status_lbl.configure(text="Erro ao processar planilha", text_color="#E74C3C")
        self.progress_detail_lbl.configure(text=f"Detalhes do erro: {error_message}")
        messagebox.showerror("Erro na Auditoria", f"Ocorreu um erro durante o processamento:\n\n{error_message}")

    def _open_generated_file(self):
        out_path = self.output_file_path.get()
        if out_path and os.path.exists(out_path):
            try:
                os.startfile(out_path)
            except Exception:
                os.startfile(os.path.dirname(out_path))


if __name__ == "__main__":
    app = AuditorComentariosApp()
    app.mainloop()
