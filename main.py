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

# Configuração global de aparência Apple Liquid Glass
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LiquidGlassCard(ctk.CTkFrame):
    """Card arredondado estilo Apple Liquid Glass (Glassmorphism minimalista)"""
    def __init__(self, master, corner_radius=22, fg_color="#232329", border_color="#363640", border_width=1, **kwargs):
        super().__init__(
            master=master,
            corner_radius=corner_radius,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            **kwargs
        )


class MetricBadge(ctk.CTkFrame):
    """Badge de métrica individual estilo painel Apple"""
    def __init__(self, master, label, value, color="#0A84FF", **kwargs):
        super().__init__(
            master=master,
            corner_radius=16,
            fg_color="#1D1D22",
            border_color="#2E2E36",
            border_width=1,
            **kwargs
        )
        self.label_lbl = ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#A0A0AD"
        )
        self.label_lbl.pack(pady=(12, 2), padx=14)
        
        self.value_lbl = ctk.CTkLabel(
            self, text=str(value), font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=color
        )
        self.value_lbl.pack(pady=(0, 12), padx=14)

    def update_value(self, value):
        self.value_lbl.configure(text=str(value))


class AppleLiquidGlassApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela Principal
        self.title("Validador de Comentários — Apple Liquid Glass OS")
        self.geometry("960x720")
        self.minsize(860, 640)
        self.configure(fg_color="#121215")

        # Variáveis de Controle
        self.selected_file_path = ctk.StringVar(value="")
        self.sheet_name_var = ctk.StringVar(value="Aud_Coment_Geral")
        self.output_file_path = ctk.StringVar(value="")
        self.is_processing = False

        # Layout Principal (Grid 1 coluna, 3 linhas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_main_content()
        self._build_footer()

    def _build_header(self):
        """Cabeçalho minimalista estilo macOS"""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=36, pady=(28, 12), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Ícone visual estilo Apple OS
        icon_lbl = ctk.CTkLabel(
            header_frame,
            text="✦",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#0A84FF",
            width=50,
            height=50,
            fg_color="#1C1C22",
            corner_radius=16
        )
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(0, 16))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Validador de Comentários PDA",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        title_lbl.grid(row=0, column=1, sticky="w")

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text="Auditoria inteligente baseada em regras de negócio • precisão e conformidade instantânea",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8E8E99",
            anchor="w"
        )
        subtitle_lbl.grid(row=1, column=1, sticky="w")

    def _build_main_content(self):
        """Painel central com seleção de arquivo, progresso e métricas"""
        self.content_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color="#2E2E36", scrollbar_button_hover_color="#454552"
        )
        self.content_frame.grid(row=1, column=0, padx=32, pady=8, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)

        # CARD 1: SELEÇÃO DO ARQUIVO (Glass Card)
        self.file_card = LiquidGlassCard(self.content_frame, corner_radius=24, fg_color="#1A1A1F", border_color="#2B2B33")
        self.file_card.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        self.file_card.grid_columnconfigure(0, weight=1)

        card_title = ctk.CTkLabel(
            self.file_card,
            text="Arquivo de Auditoria (.xlsx, .xlsm, .csv)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E2E2E8"
        )
        card_title.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        # Container do input de arquivo
        file_input_frame = ctk.CTkFrame(self.file_card, fg_color="transparent")
        file_input_frame.grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        file_input_frame.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            file_input_frame,
            textvariable=self.selected_file_path,
            placeholder_text="Nenhum arquivo selecionado... Clique em 'Selecionar Planilha'",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=46,
            corner_radius=14,
            fg_color="#121215",
            border_color="#33333D",
            text_color="#FFFFFF"
        )
        self.file_entry.grid(row=0, column=0, padx=(0, 12), sticky="ew")

        select_btn = ctk.CTkButton(
            file_input_frame,
            text="Selecionar Planilha",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=46,
            corner_radius=14,
            fg_color="#0A84FF",
            hover_color="#0066CC",
            command=self._select_file
        )
        select_btn.grid(row=0, column=1)

        # Configurações adicionais de aba e saída
        options_frame = ctk.CTkFrame(self.file_card, fg_color="#15151A", corner_radius=16)
        options_frame.grid(row=2, column=0, padx=24, pady=(0, 20), sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        sheet_lbl = ctk.CTkLabel(
            options_frame,
            text="Nome da Aba Excel:",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#A0A0AD"
        )
        sheet_lbl.grid(row=0, column=0, padx=(18, 12), pady=16, sticky="w")

        self.sheet_entry = ctk.CTkEntry(
            options_frame,
            textvariable=self.sheet_name_var,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=38,
            corner_radius=10,
            fg_color="#1C1C22",
            border_color="#30303A"
        )
        self.sheet_entry.grid(row=0, column=1, padx=(0, 18), pady=16, sticky="ew")

        # CARD 2: PROGRESSO DA VALIDAÇÃO (Inicialmente oculto ou discreto)
        self.progress_card = LiquidGlassCard(self.content_frame, corner_radius=24, fg_color="#1A1A1F", border_color="#2B2B33")
        self.progress_card.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        self.progress_card.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Pronto para iniciar a validação",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#A0A0AD"
        )
        self.status_lbl.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_card,
            height=10,
            corner_radius=5,
            fg_color="#121215",
            progress_color="#0A84FF"
        )
        self.progress_bar.grid(row=1, column=0, padx=24, pady=(0, 14), sticky="ew")
        self.progress_bar.set(0)

        self.progress_detail_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Selecione um arquivo Excel para carregar e inspecionar",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#6C6C77"
        )
        self.progress_detail_lbl.grid(row=2, column=0, padx=24, pady=(0, 20), sticky="w")

        # CARD 3: DASHBOARD DE RESULTADOS (Liquid Glass Grid)
        self.results_card = LiquidGlassCard(self.content_frame, corner_radius=24, fg_color="#1A1A1F", border_color="#2B2B33")
        self.results_card.grid(row=2, column=0, pady=(0, 20), sticky="ew")
        self.results_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        results_title = ctk.CTkLabel(
            self.results_card,
            text="Indicadores e Distribuição da Auditoria",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#E2E2E8"
        )
        results_title.grid(row=0, column=0, columnspan=4, padx=24, pady=(20, 14), sticky="w")

        # Badges de métricas
        self.badges = {}
        metric_configs = [
            ("Conforme (C)", "C", "#30D158", 1, 0),
            ("Fora Padrão (CFP)", "CFP", "#FF453A", 1, 1),
            ("Sem Comentário (SC)", "SC", "#FF9F0A", 1, 2),
            ("Falta Leitura (FL)", "FL", "#BF5AF2", 1, 3),
            ("Nota Incorreta (NI)", "NI", "#FF375F", 2, 0),
            ("Espaço Excesso (EE)", "EE", "#64D2FF", 2, 1),
            ("Coment. Incorreto (CI)", "CI", "#FFD60A", 2, 2),
            ("Caractere Esp. (UCE)", "UCE", "#AC8E68", 2, 3),
        ]

        for label, key, color, row, col in metric_configs:
            badge = MetricBadge(self.results_card, label=label, value="-", color=color)
            badge.grid(row=row, column=col, padx=10, pady=8, sticky="nsew")
            self.badges[key] = badge

        # Espaçamento inferior no card de resultados
        ctk.CTkLabel(self.results_card, text="", height=10).grid(row=3, column=0, columnspan=4)

    def _build_footer(self):
        """Rodapé com botão principal de ação e botões de abertura de arquivo"""
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, padx=36, pady=(8, 28), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)

        self.action_btn = ctk.CTkButton(
            footer_frame,
            text="▶   Executar Auditoria e Validação",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=54,
            corner_radius=18,
            fg_color="#0A84FF",
            hover_color="#0066CC",
            command=self._start_validation_thread
        )
        self.action_btn.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        self.open_excel_btn = ctk.CTkButton(
            footer_frame,
            text="📁   Abrir Planilha Gerada",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=54,
            width=210,
            corner_radius=18,
            fg_color="#2E2E36",
            hover_color="#3D3D47",
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
            # Definir arquivo de saída automaticamente na mesma pasta
            base_dir = os.path.dirname(file_path)
            file_name, file_ext = os.path.splitext(os.path.basename(file_path))
            out_path = os.path.join(base_dir, f"{file_name}_VALIDADO.xlsx")
            self.output_file_path.set(out_path)
            self.status_lbl.configure(text=f"Pronto para analisar: {os.path.basename(file_path)}", text_color="#30D158")
            self.progress_detail_lbl.configure(text=f"Saída será gravada em: {out_path}")

    def _start_validation_thread(self):
        if self.is_processing:
            return
        file_path = self.selected_file_path.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Atenção", "Por favor, selecione um arquivo válido antes de executar a análise.")
            return

        self.is_processing = True
        self.action_btn.configure(state="disabled", text="⏳   Analisando com Regras de Negócio...")
        self.open_excel_btn.configure(state="disabled")
        self.progress_bar.set(0.1)
        self.status_lbl.configure(text="Carregando planilha e normalizando colunas...", text_color="#0A84FF")
        self.progress_detail_lbl.configure(text="Aguarde enquanto os dados são lidos na memória...")

        # Rodar processamento em thread separada para não travar a UI Apple Liquid Glass
        threading.Thread(target=self._run_validation_pipeline, args=(file_path,), daemon=True).start()

    def _run_validation_pipeline(self, file_path):
        start_time = time.time()
        try:
            aba = self.sheet_name_var.get().strip() or None
            
            # Passo 1: Carregar dados
            self.progress_bar.set(0.25)
            self.status_lbl.configure(text="Carregando dados da planilha...")
            
            # Tentar importar carregar_dados de validar_comentarios
            try:
                from src.validar_comentarios import carregar_dados, normalizar_colunas
                df = carregar_dados(file_path, aba)
            except Exception:
                # Fallback direto caso importação falhe
                if file_path.endswith('.xlsx') or file_path.endswith('.xls') or file_path.endswith('.xlsm'):
                    xls = pd.ExcelFile(file_path)
                    aba_use = aba if aba and aba in xls.sheet_names else xls.sheet_names[0]
                    df = pd.read_excel(file_path, sheet_name=aba_use, dtype={"Nº_Serie": str})
                else:
                    df = pd.read_csv(file_path, sep=';', dtype={"Nº_Serie": str})
                df.columns = [str(col).strip().replace('\n', '').replace('\r', '').replace('.', '').replace(' ', '_') for col in df.columns]

            self.progress_bar.set(0.50)
            self.status_lbl.configure(text=f"Analisando {len(df):,} comentários com Regras de Negócio...")
            self.progress_detail_lbl.configure(text="Verificando prefixos, tokens S, notas e formatações de poste...")

            # Encontrar coluna de análise
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

            # Passo 2: Aplicar validação por regras
            try:
                from src.validation_rules import aplicar_validacao
                df = aplicar_validacao(df, coluna_comentario='Coment_leitura', coluna_nota='Nota_leit', coluna_analise='ANÁLISE')
            except Exception as e:
                from validation_rules import applying_validation as aplicar_validacao_alt
                df = aplicar_validacao_alt(df, coluna_comentario='Coment_leitura', coluna_nota='Nota_leit', coluna_analise='ANÁLISE')

            self.progress_bar.set(0.75)
            self.status_lbl.configure(text="Salvando arquivo Excel validado na mesma pasta...")
            self.progress_detail_lbl.configure(text="Gravando planilha com todas as análises geradas...")

            # Passo 3: Salvar Excel de saída
            out_path = self.output_file_path.get()
            df.to_excel(out_path, index=False)

            elapsed = round(time.time() - start_time, 1)
            self.progress_bar.set(1.0)
            self.status_lbl.configure(text=f"✦ Auditoria Concluída com Sucesso em {elapsed}s!", text_color="#30D158")
            self.progress_detail_lbl.configure(text=f"Arquivo gravado perfeitamente em: {out_path}")

            # Calcular distribuição
            dist = df['ANÁLISE'].value_counts().to_dict()
            for key in self.badges:
                val = dist.get(key, 0)
                self.badges[key].update_value(f"{val:,}".replace(',', '.'))

            # Atualizar UI na thread principal
            self.after(10, self._on_validation_success)

        except Exception as e:
            err_msg = str(e)
            self.after(10, lambda: self._on_validation_error(err_msg))

    def _on_validation_success(self):
        self.is_processing = False
        self.action_btn.configure(state="normal", text="▶   Executar Auditoria e Validação")
        self.open_excel_btn.configure(state="normal", fg_color="#30D158", hover_color="#24B34B")
        messagebox.showinfo("Sucesso", "A auditoria da planilha foi concluída com êxito!\n\nArquivo validado gravado na pasta original.")

    def _on_validation_error(self, error_message):
        self.is_processing = False
        self.action_btn.configure(state="normal", text="▶   Executar Auditoria e Validação")
        self.status_lbl.configure(text="Erro ao processar planilha", text_color="#FF453A")
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
    app = AppleLiquidGlassApp()
    app.mainloop()
