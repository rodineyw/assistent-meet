import sys
import time
import typer
import logging
from rich.console import Console
from rich.table import Table

from utils.logger_config import setup_logging

# Setup global logging before any other imports
setup_logging()
logger = logging.getLogger("Main")

app = typer.Typer(help="Assistente Meet - Transcritor de Reuniões Offline")

@app.command()
def devices():
    """List available audio input, output and loopback devices."""
    import soundcard as sc
    console = Console()
    
    # Microphones Table
    mic_table = Table(title="[bold violet]Microfones Disponíveis[/bold violet]")
    mic_table.add_column("Nome do Dispositivo", style="cyan")
    mic_table.add_column("Canais", style="magenta", justify="center")
    mic_table.add_column("Padrão", style="green", justify="center")
    
    default_mic = None
    try:
        default_mic = sc.default_microphone()
    except Exception:
        pass
        
    for m in sc.all_microphones():
        is_default = "Sim" if default_mic and m.name == default_mic.name else "Não"
        mic_table.add_row(m.name, str(m.channels), is_default)
        
    # Speakers Table
    spk_table = Table(title="[bold violet]Dispositivos de Saída (Speakers)[/bold violet]")
    spk_table.add_column("Nome do Dispositivo", style="cyan")
    spk_table.add_column("Canais", style="magenta", justify="center")
    spk_table.add_column("Padrão", style="green", justify="center")
    
    default_spk = None
    try:
        default_spk = sc.default_speaker()
    except Exception:
        pass
        
    for s in sc.all_speakers():
        is_default = "Sim" if default_spk and s.name == default_spk.name else "Não"
        spk_table.add_row(s.name, str(s.channels), is_default)
        
    # Loopback Table
    loop_table = Table(title="[bold violet]Captura do Sistema (Loopback/WASAPI)[/bold violet]")
    loop_table.add_column("Nome do Dispositivo de Saída", style="cyan")
    loop_table.add_column("Canais", style="magenta", justify="center")
    loop_table.add_column("Padrão", style="green", justify="center")
    
    for l in sc.all_microphones(include_loopback=True):
        if l.isloopback:
            is_default = "Sim" if default_spk and l.name == default_spk.name else "Não"
            loop_table.add_row(l.name, str(l.channels), is_default)
            
    console.print(mic_table)
    console.print(spk_table)
    console.print(loop_table)

@app.command()
def record(
    meeting_name: str = typer.Option("reuniao", "--meeting-name", "-n", help="Nome do assunto ou reunião"),
    language: str = typer.Option("pt", "--language", "-l", help="Código do idioma (ex: pt, en)"),
    model: str = typer.Option("small", "--model", "-m", help="Tamanho do modelo Whisper (tiny, base, small, medium)"),
    mic_name: str = typer.Option(None, "--mic-name", help="Filtrar microfone por nome (substring)"),
    speaker_name: str = typer.Option(None, "--speaker-name", help="Filtrar saída de áudio para loopback por nome"),
    no_mic: bool = typer.Option(False, "--no-mic", help="Desativar captura do microfone"),
    no_speaker: bool = typer.Option(False, "--no-speaker", help="Desativar captura do som do sistema (loopback)"),
    no_postprocess: bool = typer.Option(False, "--no-postprocess", help="Desativar pós-processamento de IA com Ollama local")
):
    """Start recording and transcribing the meeting in real-time."""
    from utils.meeting_manager import MeetingManager
    
    console = Console()
    console.print(f"[bold green]Iniciando assistente de reuniões offline...[/bold green]")
    console.print(f"Reunião: [cyan]{meeting_name}[/cyan] | Idioma: [cyan]{language}[/cyan] | Modelo: [cyan]{model}[/cyan]\n")
    
    def on_trans(source, start_time, end_time, text):
        total_sec = int(start_time)
        m = total_sec // 60
        s = total_sec % 60
        time_str = f"{m:02d}:{s:02d}"
        
        color = "green" if source == "Você" else "magenta"
        console.print(f"[{color}][{source}] ({time_str}): {text}[/{color}]")
        
    def on_stat(status):
        console.print(f"[grey50][Status: {status}][/grey50]")
        
    manager = MeetingManager(
        meeting_name=meeting_name,
        language=language,
        model_size=model,
        no_mic=no_mic,
        no_speaker=no_speaker,
        mic_name=mic_name,
        speaker_name=speaker_name,
        no_postprocess=no_postprocess,
        on_transcription=on_trans,
        on_status=on_stat
    )
    
    success = manager.start_meeting()
    if not success:
        console.print("[bold red]Falha ao iniciar reunião.[/bold red]")
        raise typer.Exit(code=1)
        
    console.print("\n[bold yellow]Pressione CTRL+C para encerrar e processar a gravação...[/bold yellow]\n")
    
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Encerrando captura e iniciando pós-processamento...[/bold yellow]")
        final_path = manager.stop_meeting()
        console.print(f"[bold green]Gravação finalizada e salva em:[/bold green] [cyan]{final_path}[/cyan]")

def main():
    if len(sys.argv) > 1:
        app()
    else:
        from ui.main_window import run_gui
        run_gui()

if __name__ == "__main__":
    main()
