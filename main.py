import os
import sys
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

# Adicionar o diretório raiz e src ao PATH para garantir importações
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    from src.validar_comentarios import carregar_dados, normalizar_colunas
    from src.validation_rules import aplicar_validacao
except ImportError:
    try:
        from validation_rules import aplicar_validacao
    except ImportError:
        pass

# Configuração de tema escuro moderno (Prisma / Foundations Space-Grey & Coral Glow)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RaisedGlassCard(ctk.CTkFrame):
    """Card com elevação e profundidade visual (estilo Foundations Raised/Inset Glass)"""
    def __init__(self, master, corner_radius=20, fg_color="#242632", border_color="#3A3D4E", border_width=1, **kwargs):
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
    def __init__(self, master, label, value, color="#FF5C4D", **kwargs):
        super().__init__(
            master=master,
            corner_radius=14,
            fg_color="#1B1D26",
            border_color="#2E3140",
            border_width=1,
            **kwargs
        )
        self.label_lbl = ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#9A9DB0"
        )
        self.label_lbl.pack(pady=(10, 2), padx=12)
        
        self.value_lbl = ctk.CTkLabel(
            self, text=str(value), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=color
        )
        self.value_lbl.pack(pady=(0, 10), padx=12)

    def update_value(self, value):
        self.value_lbl.configure(text=str(value))


class AuditorComentariosApp(ctk.CTk):
    """Painel principal do Auditor de Comentários PDA - Design Foundations Space-Grey & Coral"""
    def __init__(self):
        super().__init__()

        # Configuração da Janela Principal
        self.title("Auditor de Comentários — Sistema de Validação PDA")
        self.geometry("1060x740")
        self.minsize(920, 660)
        self.configure(fg_color="#14151C")

        # Variáveis de Controle
        self.selected_file_path = ctk.StringVar(value="")
        self.sheet_name_var = ctk.StringVar(value="Aud_Coment_Geral")
        self.output_file_path = ctk.StringVar(value="")
        self.is_processing = False

        # Grid principal: 2 colunas (Sidebar lateral esquerdo + Painel Central de Cards)
        self.grid_columnconfigure(0, weight=0, minsize=240)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_panel()

    def _build_sidebar(self):
        """Painel lateral esquerdo com navegação e resumo do workspace"""
        sidebar_frame = ctk.CTkFrame(self, fg_color="#1C1D26", corner_radius=0, border_color="#2A2C38", border_width=1)
        sidebar_frame.grid(row=0, column=0, sticky="nsew")
        sidebar_frame.grid_rowconfigure(6, weight=1)

        # Logo e Identidade
        logo_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=22, pady=(26, 20), sticky="ew")

        icon_box = ctk.CTkLabel(
            logo_frame,
            text="⬡",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color="#FF5C4D",
            width=42,
            height=42,
            fg_color="#242632",
            corner_radius=12
        )
        icon_box.grid(row=0, column=0, padx=(0, 12))

        title_lbl = ctk.CTkLabel(
            logo_frame,
            text="Auditor PDA\nWorkspace",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#FFFFFF",
            justify="left"
        )
        title_lbl.grid(row=0, column=1, sticky="w")

        # Divisor
        ctk.CTkFrame(sidebar_frame, height=1, fg_color="#2A2C38").grid(row=1, column=0, sticky="ew", padx=16, pady=6)

        # Botões de navegação lateral (estilo PrismaFlow)
        nav_items = [
            ("⚡ Visão Geral", True),
            ("📁 Planilhas", False),
            ("⚙ Regras e Tokens", False),
            ("📊 Histórico Auditoria", False),
        ]

        for idx, (label, active) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                sidebar_frame,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold" if active else "normal"),
                fg_color="#2C2E3C" if active else "transparent",
                text_color="#FF5C4D" if active else "#9A9DB0",
                hover_color="#262834",
                anchor="w",
                height=42,
                corner_radius=12
            )
            btn.grid(row=idx, column=0, padx=16, pady=4, sticky="ew")

        # Card de informações operacionais na parte inferior do sidebar
        info_card = RaisedGlassCard(sidebar_frame, corner_radius=14, fg_color="#181920", border_color="#2A2C38")
        info_card.grid(row=7, column=0, padx=16, pady=24, sticky="ew")

        ctk.CTkLabel(
            info_card,
            text="Validador Regras 2.0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#E2E4F0"
        ).pack(pady=(12, 4), padx=14, anchor="w")

        ctk.CTkLabel(
            info_card,
            text="Múltiplos pares de código/leitura,\nprefixos S e checagem de notas.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#7A7D8F",
            justify="left"
        ).pack(pady=(0, 12), padx=14, anchor="w")

    def _build_main_panel(self):
        """Painel central de cards e execução"""
        main_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color="#2A2C38", scrollbar_button_hover_color="#3A3D4E"
        )
        main_scroll.grid(row=0, column=1, padx=28, pady=20, sticky="nsew")
        main_scroll.grid_columnconfigure(0, weight=1)

        # Cabeçalho da área principal
        header_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(10, 20), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Validação de Comentários de Leitura",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_frame,
            text="Carregue a planilha de auditoria para processar e classificar automaticamente cada nota em segundos.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8E92A4"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # CARD 1: SELEÇÃO DA PLANILHA (Raised Glass Card com botão Coral)
        file_card = RaisedGlassCard(main_scroll, corner_radius=18, fg_color="#1E202A", border_color="#2E3140")
        file_card.grid(row=1, column=0, pady=(0, 18), sticky="ew")
        file_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            file_card,
            text="Arquivo de Auditoria (.xlsx, .xlsm, .csv)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E2E4F0"
        ).grid(row=0, column=0, padx=22, pady=(18, 10), sticky="w")

        # Input de arquivo
        file_input = ctk.CTkFrame(file_card, fg_color="transparent")
        file_input.grid(row=1, column=0, padx=22, pady=(0, 16), sticky="ew")
        file_input.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            file_input,
            textvariable=self.selected_file_path,
            placeholder_text="Nenhuma planilha carregada... Clique no botão ao lado para selecionar",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=46,
            corner_radius=12,
            fg_color="#14151C",
            border_color="#2E3140",
            text_color="#FFFFFF"
        )
        self.file_entry.grid(row=0, column=0, padx=(0, 12), sticky="ew")

        select_btn = ctk.CTkButton(
            file_input,
            text="📁 Selecionar Planilha",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=46,
            width=170,
            corner_radius=12,
            fg_color="#FF5C4D",
            hover_color="#E84A3B",
            text_color="#FFFFFF",
            command=self._select_file
        )
        select_btn.grid(row=0, column=1)

        # Opções de Aba
        options_box = ctk.CTkFrame(file_card, fg_color="#161820", corner_radius=12, border_color="#242632", border_width=1)
        options_box.grid(row=2, column=0, padx=22, pady=(0, 18), sticky="ew")
        options_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            options_box,
            text="Nome da Aba Excel:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#A0A4B8"
        ).grid(row=0, column=0, padx=(16, 12), pady=14, sticky="w")

        self.sheet_entry = ctk.CTkEntry(
            options_box,
            textvariable=self.sheet_name_var,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36,
            corner_radius=8,
            fg_color="#1C1D26",
            border_color="#2E3140"
        )
        self.sheet_entry.grid(row=0, column=1, padx=(0, 16), pady=14, sticky="ew")

        # CARD 2: STATUS E BARRA DE PROGRESSO
        self.progress_card = RaisedGlassCard(main_scroll, corner_radius=18, fg_color="#1E202A", border_color="#2E3140")
        self.progress_card.grid(row=2, column=0, pady=(0, 18), sticky="ew")
        self.progress_card.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Pronto para iniciar auditoria operacional",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#A0A4B8"
        )
        self.status_lbl.grid(row=0, column=0, padx=22, pady=(18, 10), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_card,
            height=10,
            corner_radius=5,
            fg_color="#14151C",
            progress_color="#FF5C4D"
        )
        self.progress_bar.grid(row=1, column=0, padx=22, pady=(0, 12), sticky="ew")
        self.progress_bar.set(0)

        self.progress_detail_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Selecione um arquivo .xlsm ou .xlsx para análise de regras de negócio",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#7A7D8F"
        )
        self.progress_detail_lbl.grid(row=2, column=0, padx=22, pady=(0, 18), sticky="w")

        # CARD 3: DASHBOARD DE MÉTRICAS (GRID)
        self.results_card = RaisedGlassCard(main_scroll, corner_radius=18, fg_color="#1E202A", border_color="#2E3140")
        self.results_card.grid(row=3, column=0, pady=(0, 20), sticky="ew")
        self.results_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            self.results_card,
            text="Indicadores de Conformidade (Análises Geradas)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E2E4F0"
        ).grid(row=0, column=0, columnspan=4, padx=22, pady=(18, 12), sticky="w")

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

        ctk.CTkLabel(self.results_card, text="", height=8).grid(row=3, column=0, columnspan=4)

        # RODAPÉ DE AÇÃO PRINCIPAL
        footer_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        footer_frame.grid(row=4, column=0, pady=(4, 20), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        self.action_btn = ctk.CTkButton(
            footer_frame,
            text="▶ Executar Auditoria e Gerar Planilha",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=52,
            corner_radius=14,
            fg_color="#FF5C4D",
            hover_color="#E84A3B",
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
            fg_color="#2C2E3C",
            hover_color="#3A3D4E",
            text_color="#FFFFFF",
            state="disabled",
            command=self._open_generated_file
        )
        self.open_excel_btn.grid(row=0, column=1)

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
            self.progress_detail_lbl.configure(text=f"Destino: {out_path}")

    def _start_validation_thread(self):
        if self.is_processing:
            return
        file_path = self.selected_file_path.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Atenção", "Por favor, selecione um arquivo válido antes de executar a análise.")
            return

        self.is_processing = True
        self.action_btn.configure(state="disabled", text="⏳ Processando Regras de Negócio...")
        self.open_excel_btn.configure(state="disabled")
        self.progress_bar.set(0.1)
        self.status_lbl.configure(text="Carregando planilha e normalizando colunas...", text_color="#FF5C4D")
        self.progress_detail_lbl.configure(text="Lendo estrutura de dados na memória...")

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

            try:
                from src.validation_rules import aplicar_validacao
                df = aplicar_validacao(df, coluna_comentario='Coment_leitura', coluna_nota='Nota_leit', coluna_analise='ANÁLISE')
            except Exception:
                from validation_rules import applying_validation as aplicar_validacao_alt
                df = aplicar_validacao_alt(df, coluna_comentario='Coment_leitura', coluna_nota='Nota_leit', coluna_analise='ANÁLISE')

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
