import os
import json
import logging
import datetime
from utils.app_paths import get_transcripts_dir

logger = logging.getLogger("TextWriter")

class TextWriter:
    def __init__(self, meeting_name, start_time_struct):
        self.meeting_name = meeting_name
        self.start_time_struct = start_time_struct  # datetime object
        
        # Format names
        self.folder_date_str = self.start_time_struct.strftime("%Y-%m-%d_%H-%M-%S")
        
        # Clean meeting name for folder safety
        safe_meeting_name = "".join(c for c in meeting_name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_meeting_name = safe_meeting_name.replace(" ", "-")
        if not safe_meeting_name:
            safe_meeting_name = "reuniao"
            
        self.folder_name = f"{self.folder_date_str}_{safe_meeting_name}"
        self.folder_path = os.path.join(get_transcripts_dir(), self.folder_name)
        os.makedirs(self.folder_path, exist_ok=True)
        
        self.transcript_path = os.path.join(self.folder_path, "transcript.md")
        self.events_path = os.path.join(self.folder_path, "events.jsonl")
        
        # Write file headers
        self._write_headers()
        
    def _write_headers(self):
        try:
            if not os.path.exists(self.transcript_path):
                with open(self.transcript_path, "w", encoding="utf-8") as f:
                    f.write(f"# Transcrição da Reunião - {self.meeting_name}\n\n")
                    f.write(f"- **Data:** {self.start_time_struct.strftime('%d/%m/%Y')}\n")
                    f.write(f"- **Início:** {self.start_time_struct.strftime('%H:%M:%S')}\n\n")
                    f.write("---\n\n")
            logger.info(f"Escritor inicializado em: {self.folder_path}")
        except Exception as e:
            logger.error(f"Erro ao escrever cabeçalhos: {e}")
            
    def format_timestamp(self, seconds):
        """Formats time in seconds into MM:SS or HH:MM:SS."""
        seconds = max(0.0, seconds)
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
            
    def append_event(self, source, start_time, end_time, text):
        """Appends transcription event incrementally to markdown and JSONL."""
        if not text or not text.strip():
            return
            
        time_str = self.format_timestamp(start_time)
        clean_text = text.strip()
        
        try:
            # Markdown update
            with open(self.transcript_path, "a", encoding="utf-8") as f:
                f.write(f"**[{source}]** ({time_str}):\n{clean_text}\n\n")
                
            # JSONL update
            event = {
                "timestamp": start_time,
                "duration": max(0.0, end_time - start_time),
                "speaker": source,
                "text": clean_text
            }
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                
            logger.debug(f"Evento anexado de [{source}] às {time_str}")
        except Exception as e:
            logger.error(f"Erro ao anexar evento: {e}")
            
    def write_diarized(self, diarized_events):
        """Writes diarized version of transcripts (Markdown and JSONL)."""
        diarized_transcript_path = os.path.join(self.folder_path, "transcript_diarizado.md")
        diarized_events_path = os.path.join(self.folder_path, "events_diarized.jsonl")
        
        try:
            with open(diarized_transcript_path, "w", encoding="utf-8") as f:
                f.write(f"# Transcrição Diarizada - {self.meeting_name}\n\n")
                f.write(f"- **Data:** {self.start_time_struct.strftime('%d/%m/%Y')}\n")
                f.write(f"- **Início:** {self.start_time_struct.strftime('%H:%M:%S')}\n\n")
                f.write("---\n\n")
                
                for ev in diarized_events:
                    time_str = self.format_timestamp(ev["timestamp"])
                    f.write(f"**[{ev['speaker_label']}]** ({time_str}):\n{ev['text']}\n\n")
                    
            with open(diarized_events_path, "w", encoding="utf-8") as f:
                for ev in diarized_events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                    
            logger.info("Transcrição diarizada gravada.")
        except Exception as e:
            logger.error(f"Erro ao gravar diarização: {e}")
            
    def write_postprocessed(self, revised_transcript, report):
        """Writes LLM revised transcript and meeting report."""
        revised_path = os.path.join(self.folder_path, "transcript_revisado.md")
        report_path = os.path.join(self.folder_path, "meeting_report.md")
        
        try:
            if revised_transcript:
                with open(revised_path, "w", encoding="utf-8") as f:
                    f.write(revised_transcript)
                logger.info("Transcrição revisada gravada.")
                
            if report:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info("Relatório de reunião gravado.")
        except Exception as e:
            logger.error(f"Erro ao gravar arquivos pós-processados: {e}")
            
    def rename_folder_with_topic(self, topic):
        """Renames the transcripts folder using the inferred meeting topic/theme."""
        if not topic or not topic.strip():
            return self.folder_path
            
        # Standardize topic for folder naming
        clean_topic = "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_")).strip()
        clean_topic = clean_topic.replace(" ", "-")[:40]
        if not clean_topic:
            return self.folder_path
            
        new_folder_name = f"{self.folder_date_str}_{clean_topic}"
        new_folder_path = os.path.join(get_transcripts_dir(), new_folder_name)
        
        # Don't do anything if they are the same
        if self.folder_path == new_folder_path:
            return self.folder_path
            
        try:
            # If the destination already exists, we append a suffix
            counter = 1
            temp_path = new_folder_path
            while os.path.exists(temp_path):
                temp_path = f"{new_folder_path}_{counter}"
                counter += 1
            new_folder_path = temp_path
            
            os.rename(self.folder_path, new_folder_path)
            logger.info(f"Pasta renomeada de {self.folder_path} para {new_folder_path}")
            
            # Update paths
            self.folder_path = new_folder_path
            self.transcript_path = os.path.join(self.folder_path, "transcript.md")
            self.events_path = os.path.join(self.folder_path, "events.jsonl")
            
            return new_folder_path
        except Exception as e:
            logger.error(f"Erro ao renomear pasta para o tema: {e}")
            return self.folder_path
