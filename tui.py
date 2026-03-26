"""
SynthForge Terminal UI
Textual ile interaktif terminal arayüzü
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Input, Label, ListItem, ListView,
    Log, OptionList, Placeholder, ProgressBar, RadioButton, 
    RadioSet, RichLog, Select, Static, TabbedContent, TabPane,
    TextArea, DataTable, Rule, LoadingIndicator, Markdown
)
from textual.widget import Widget

from rich.table import Table
from rich.panel import Panel
from rich.text import Text

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.types import DataType, ExportFormat, DataSpec, FieldSpec
from templates.specs import TEMPLATES, get_template, list_templates


# ── CSS Styles ──────────────────────────────────────────────────────────────

CSS = """
Screen {
    background: $surface;
}

#main-container {
    width: 100%;
    height: 100%;
}

#sidebar {
    width: 28;
    dock: left;
    background: $panel;
    border-right: solid $primary;
    padding: 1;
}

#content {
    width: 100%;
    height: 100%;
    padding: 1 2;
}

.section-title {
    text-style: bold;
    color: $text;
    padding: 1 0;
}

.form-label {
    margin-top: 1;
    color: $text-muted;
}

.form-input {
    margin-bottom: 1;
}

#prompt-input {
    height: 5;
    margin: 1 0;
}

#generate-btn {
    margin-top: 1;
    width: 100%;
}

#output-log {
    height: 100%;
    border: solid $primary;
    background: $surface-darken-1;
}

#spec-preview {
    height: 12;
    border: solid $secondary;
    background: $surface-darken-1;
    padding: 1;
    overflow: auto;
}

#template-list {
    height: 10;
    border: solid $accent;
}

.status-bar {
    dock: bottom;
    height: 3;
    background: $panel;
    padding: 0 2;
}

#progress-container {
    height: 3;
    margin-top: 1;
}

RadioSet {
    height: auto;
    border: none;
    padding: 0;
}

RadioButton {
    height: 1;
    padding: 0;
}

Select {
    width: 100%;
}

#field-table {
    height: 15;
    margin: 1 0;
}

.help-text {
    color: $text-muted;
    text-style: italic;
}

#result-panel {
    border: double $success;
    padding: 1;
    margin: 1 0;
    background: $surface-darken-1;
}

.error-text {
    color: $error;
}

.success-text {
    color: $success;
}

LoadingIndicator {
    height: 3;
}
"""


# ── Main Application ────────────────────────────────────────────────────────

class SynthForgeApp(App):
    """SynthForge Terminal UI Application."""
    
    TITLE = "SynthForge"
    SUB_TITLE = "Sentetik Veri Üretici"
    CSS = CSS
    
    BINDINGS = [
        Binding("q", "quit", "Çıkış", show=True),
        Binding("g", "generate", "Üret", show=True),
        Binding("t", "show_templates", "Şablonlar", show=True),
        Binding("c", "clear_log", "Temizle", show=True),
        Binding("d", "toggle_dark", "Tema", show=True),
        Binding("?", "show_help", "Yardım", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.current_spec: DataSpec | None = None
        self.is_generating = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal(id="main-container"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static(" VERİ TİPİ", classes="section-title")
                yield RadioSet(
                    RadioButton("Tabular", id="type-tabular", value=True),
                    RadioButton("NLP", id="type-nlp"),
                    RadioButton("Timeseries", id="type-timeseries"),
                    RadioButton("Log", id="type-log"),
                    id="data-type-selector"
                )
                
                yield Rule()
                
                yield Static(" FORMAT", classes="section-title")
                yield Select(
                    [(f.value.upper(), f.value) for f in ExportFormat],
                    value="jsonl",
                    id="format-select"
                )
                
                yield Rule()
                
                yield Static(" KAYIT SAYISI", classes="section-title")
                yield Input(value="100", id="row-count-input", type="integer")
                
                yield Rule()
                
                yield Static(" SEED", classes="section-title")
                yield Input(placeholder="Opsiyonel", id="seed-input", type="integer")
                
                yield Rule()
                
                yield Static(" ÇIKTI DİZİNİ", classes="section-title")
                yield Input(value="./output", id="output-dir-input")
            
            # Main Content
            with Vertical(id="content"):
                yield Static(" VERİ TANIMI", classes="section-title")
                yield TextArea(
                    placeholder="Veri setinizi doğal dil ile tanımlayın...\n\nÖrnek: E-ticaret sipariş verisi üret. Müşteri adı, email, ürün ismi, fiyat, miktar, sipariş tarihi ve durumu olsun.",
                    id="prompt-input"
                )
                
                with Horizontal():
                    yield Button(" Üret", id="generate-btn", variant="primary")
                    yield Button(" Şablondan", id="template-btn", variant="default")
                    yield Button(" Önizle", id="preview-btn", variant="default")
                
                with Container(id="progress-container"):
                    yield LoadingIndicator(id="loading")
                    yield ProgressBar(id="progress-bar", show_eta=False)
                
                yield Static(" ÇIKTI", classes="section-title")
                yield RichLog(id="output-log", highlight=True, markup=True)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#progress-bar", ProgressBar).display = False
        
        log = self.query_one("#output-log", RichLog)
        log.write("[bold cyan]SynthForge[/] başlatıldı!")
        log.write("")
        log.write("[dim]Doğal dil ile veri setinizi tanımlayın veya bir şablon seçin.[/]")
        log.write("[dim]Ardından [bold]Üret[/] butonuna basın veya [bold]G[/] tuşuna basın.[/]")
    
    def _get_data_type(self) -> DataType:
        """Get selected data type."""
        radio_set = self.query_one("#data-type-selector", RadioSet)
        pressed = radio_set.pressed_button
        if pressed:
            type_map = {
                "type-tabular": DataType.TABULAR,
                "type-nlp": DataType.NLP,
                "type-timeseries": DataType.TIMESERIES,
                "type-log": DataType.LOG,
            }
            return type_map.get(pressed.id, DataType.TABULAR)
        return DataType.TABULAR
    
    def _get_export_format(self) -> ExportFormat:
        """Get selected export format."""
        select = self.query_one("#format-select", Select)
        return ExportFormat(select.value)
    
    def _get_row_count(self) -> int:
        """Get row count."""
        input_widget = self.query_one("#row-count-input", Input)
        try:
            return int(input_widget.value) if input_widget.value else 100
        except ValueError:
            return 100
    
    def _get_seed(self) -> int | None:
        """Get seed value."""
        input_widget = self.query_one("#seed-input", Input)
        try:
            return int(input_widget.value) if input_widget.value else None
        except ValueError:
            return None
    
    def _get_output_dir(self) -> str:
        """Get output directory."""
        input_widget = self.query_one("#output-dir-input", Input)
        return input_widget.value or "./output"
    
    def _get_prompt(self) -> str:
        """Get prompt text."""
        textarea = self.query_one("#prompt-input", TextArea)
        return textarea.text
    
    @on(Button.Pressed, "#generate-btn")
    def on_generate_pressed(self) -> None:
        """Handle generate button press."""
        self.action_generate()
    
    @on(Button.Pressed, "#template-btn")
    def on_template_pressed(self) -> None:
        """Handle template button press."""
        self.action_show_templates()
    
    @on(Button.Pressed, "#preview-btn")
    def on_preview_pressed(self) -> None:
        """Handle preview button press."""
        self._preview_spec()
    
    def action_generate(self) -> None:
        """Generate data."""
        if self.is_generating:
            return
        
        prompt = self._get_prompt()
        if not prompt.strip():
            self._log_error("Lütfen bir veri tanımı girin!")
            return
        
        self._start_generation(prompt)
    
    @work(exclusive=True, thread=True)
    def _start_generation(self, prompt: str) -> None:
        """Run generation in background thread."""
        self.is_generating = True
        self.call_from_thread(self._show_loading, True)
        
        log = self.query_one("#output-log", RichLog)
        
        try:
            self.call_from_thread(log.write, "\n[bold cyan]═══ Üretim Başlıyor ═══[/]")
            self.call_from_thread(log.write, f"[dim]Prompt:[/] {prompt[:100]}...")
            
            from pipeline import run
            import random
            
            data_type = self._get_data_type()
            export_format = self._get_export_format()
            row_count = self._get_row_count()
            seed = self._get_seed()
            output_dir = self._get_output_dir()
            
            self.call_from_thread(log.write, f"[dim]Tip:[/] {data_type.value} | [dim]Rows:[/] {row_count} | [dim]Format:[/] {export_format.value}")
            
            if seed is not None:
                random.seed(seed)
                self.call_from_thread(log.write, f"[dim]Seed:[/] {seed}")
            
            # Step 1: Intent parsing
            self.call_from_thread(log.write, "\n[yellow] Intent parse ediliyor...[/]")
            self.call_from_thread(self._update_progress, 0.2)
            
            result = run(
                prompt=prompt,
                data_type=data_type,
                row_count=row_count,
                export_format=export_format,
                output_dir=output_dir,
                seed=seed,
                quiet=True,
            )
            
            self.call_from_thread(self._update_progress, 1.0)
            
            # Success!
            self.call_from_thread(log.write, "\n[bold green] Üretim Tamamlandı![/]")
            self.call_from_thread(log.write, f"[green]   Kayıt sayısı:[/] {len(result.dataset.records)}")
            self.call_from_thread(log.write, f"[green]   Validation:[/] {'Geçti' if result.validation.passed else 'Kısmi'} (score={result.validation.score:.2f})")
            self.call_from_thread(log.write, f"[green]   İterasyon:[/] {result.iterations}")
            self.call_from_thread(log.write, f"[green]   Dosya:[/] {result.export_path}")
            
            # Show sample
            if result.dataset.records:
                self.call_from_thread(log.write, "\n[cyan]Örnek kayıtlar:[/]")
                import json
                for i, record in enumerate(result.dataset.records[:3]):
                    self.call_from_thread(log.write, f"[dim]{i+1}.[/] {json.dumps(record, ensure_ascii=False, default=str)[:200]}")
            
        except Exception as e:
            self.call_from_thread(log.write, f"\n[bold red] Hata:[/] {str(e)}")
            import traceback
            self.call_from_thread(log.write, f"[dim]{traceback.format_exc()[:500]}[/]")
        
        finally:
            self.is_generating = False
            self.call_from_thread(self._show_loading, False)
    
    def _show_loading(self, show: bool) -> None:
        """Show/hide loading indicator."""
        loading = self.query_one("#loading", LoadingIndicator)
        progress = self.query_one("#progress-bar", ProgressBar)
        loading.display = show
        progress.display = show
        if show:
            progress.update(progress=0)
    
    def _update_progress(self, value: float) -> None:
        """Update progress bar."""
        progress = self.query_one("#progress-bar", ProgressBar)
        progress.update(progress=value)
    
    def _log_error(self, message: str) -> None:
        """Log an error message."""
        log = self.query_one("#output-log", RichLog)
        log.write(f"[bold red] {message}[/]")
    
    def _preview_spec(self) -> None:
        """Preview the spec that would be generated."""
        prompt = self._get_prompt()
        if not prompt.strip():
            self._log_error("Lütfen bir veri tanımı girin!")
            return
        
        log = self.query_one("#output-log", RichLog)
        log.write("\n[yellow]Spec önizleme için API çağrısı gerekli.[/]")
        log.write("[dim]Dry-run için CLI kullanın: python cli.py '...' --type tabular --dry-run[/]")
    
    def action_show_templates(self) -> None:
        """Show template selection screen."""
        self.push_screen(TemplateScreen())
    
    def action_clear_log(self) -> None:
        """Clear the output log."""
        log = self.query_one("#output-log", RichLog)
        log.clear()
        log.write("[dim]Log temizlendi.[/]")
    
    def action_show_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def apply_template(self, template_name: str) -> None:
        """Apply a template."""
        spec = get_template(template_name)
        if spec:
            textarea = self.query_one("#prompt-input", TextArea)
            textarea.text = spec.context
            
            # Update row count
            row_input = self.query_one("#row-count-input", Input)
            row_input.value = str(spec.row_count)
            
            # Update data type
            radio_map = {
                DataType.TABULAR: "type-tabular",
                DataType.NLP: "type-nlp",
                DataType.TIMESERIES: "type-timeseries",
                DataType.LOG: "type-log",
            }
            radio_id = radio_map.get(spec.data_type, "type-tabular")
            radio = self.query_one(f"#{radio_id}", RadioButton)
            radio.value = True
            
            log = self.query_one("#output-log", RichLog)
            log.write(f"\n[green] Şablon uygulandı:[/] {template_name}")
            log.write(f"[dim]  Tip: {spec.data_type.value} | Alanlar: {len(spec.fields)} | Kayıt: {spec.row_count}[/]")


# ── Template Selection Screen ───────────────────────────────────────────────

class TemplateScreen(ModalScreen):
    """Template selection modal."""
    
    CSS = """
    TemplateScreen {
        align: center middle;
    }
    
    #template-dialog {
        width: 80;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #template-list {
        height: 20;
        margin: 1 0;
    }
    
    #template-info {
        height: 5;
        padding: 1;
        background: $surface-darken-1;
        border: solid $secondary;
    }
    """
    
    BINDINGS = [
        Binding("escape", "dismiss", "Kapat"),
    ]
    
    def compose(self) -> ComposeResult:
        with Vertical(id="template-dialog"):
            yield Static("[bold] Şablon Seç[/]", classes="section-title")
            
            yield OptionList(
                *[f"{name} ({TEMPLATES[name].data_type.value})" for name in list_templates()],
                id="template-list"
            )
            
            yield Static("", id="template-info")
            
            with Horizontal():
                yield Button("Uygula", id="apply-btn", variant="primary")
                yield Button("İptal", id="cancel-btn", variant="default")
    
    def on_mount(self) -> None:
        self.query_one("#template-list", OptionList).focus()
    
    @on(OptionList.OptionHighlighted)
    def on_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Update info when option is highlighted."""
        templates = list_templates()
        if event.option_index < len(templates):
            template_name = templates[event.option_index]
            spec = get_template(template_name)
            if spec:
                info = self.query_one("#template-info", Static)
                info.update(
                    f"[cyan]{template_name}[/]\n"
                    f"[dim]Alanlar:[/] {len(spec.fields)} | "
                    f"[dim]Kayıt:[/] {spec.row_count}\n"
                    f"[dim]{spec.context[:60]}...[/]"
                )
    
    @on(Button.Pressed, "#apply-btn")
    @on(OptionList.OptionSelected)
    def on_apply(self, event=None) -> None:
        """Apply selected template."""
        option_list = self.query_one("#template-list", OptionList)
        if option_list.highlighted is not None:
            templates = list_templates()
            template_name = templates[option_list.highlighted]
            self.app.apply_template(template_name)
            self.dismiss()
    
    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        self.dismiss()


# ── Help Screen ─────────────────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    """Help screen modal."""
    
    CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-dialog {
        width: 70;
        height: 25;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    
    #help-content {
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("escape", "dismiss", "Kapat"),
        Binding("q", "dismiss", "Kapat"),
    ]
    
    HELP_TEXT = """
# SynthForge Yardım

## Klavye Kısayolları
- **G** : Veri üret
- **T** : Şablon seç
- **C** : Log temizle
- **D** : Tema değiştir (açık/koyu)
- **Q** : Çıkış
- **?** : Bu yardım

## Kullanım
1. Sol panelden veri tipini seçin
2. Prompt alanına veri tanımınızı yazın
3. **Üret** butonuna basın veya **G** tuşuna basın
4. Sonuçlar log alanında görünecek

## Veri Tipleri
- **Tabular**: Yapısal tablo verisi
- **NLP**: Doğal dil metinleri
- **Timeseries**: Zaman serisi
- **Log**: Sistem logları

## İpuçları
- Seed değeri ile aynı veriyi tekrar üretebilirsiniz
- Şablonlar hızlı başlangıç için idealdir
"""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Markdown(self.HELP_TEXT, id="help-content")
            yield Button("Kapat", id="close-btn", variant="primary")
    
    @on(Button.Pressed, "#close-btn")
    def on_close(self) -> None:
        self.dismiss()


# ── Entry Point ─────────────────────────────────────────────────────────────

def main():
    """Run the TUI application."""
    app = SynthForgeApp()
    app.run()


if __name__ == "__main__":
    main()
