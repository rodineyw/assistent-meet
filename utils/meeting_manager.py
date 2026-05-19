import os
import time
import queue
import logging
import datetime
import threading
import soundcard as sc
from utils.audio_capture import AudioRecorderThread
from utils.transcriber import Transcriber
from utils.text_writer import TextWriter
from utils.postprocessor import get_ollama_model, query_ollama
from utils.vad_detector import run_diarization

logger = logging.getLogger("MeetingManager")

class MeetingManager:
    def __init__(self, meeting_name="reuniao", language="pt", model_size="small", 
                 no_mic=False, no_speaker=False, mic_name=None, speaker_name=None, 
                 no_postprocess=False, on_transcription=None, on_status=None, on_rms=None):
        self.meeting_name = meeting_name
        self.language = language
        self.model_size = model_size
        self.no_mic = no_mic
        self.no_speaker = no_speaker
        self.mic_name = mic_name
        self.speaker_name = speaker_name
        self.no_postprocess = no_postprocess
        
        # Callbacks
        self.on_transcription = on_transcription  # fn(source, start_time, end_time, text)
        self.on_status = on_status                  # fn(status_text)
        self.on_rms = on_rms                        # fn(source, rms_value)
        
        # Queues and threads
        self.transcription_queue = queue.Queue()
        self.transcriber = None
        self.text_writer = None
        self.meeting_start_time = None
        self.start_time_struct = None
        
        self.mic_thread = None
        self.spk_thread = None
        self.transcription_thread = None
        self.is_recording = False
        self.is_paused = False
        
        # Audio segment archive for final diarization
        self.all_segments = []
        
    def set_status(self, text):
        logger.info(f"Status: {text}")
        if self.on_status:
            self.on_status(text)
            
    def start_meeting(self):
        """Starts recording and transcription threads."""
        self.start_time_struct = datetime.datetime.now()
        self.meeting_start_time = time.time()
        self.all_segments = []
        self.is_recording = True
        self.is_paused = False
        
        self.set_status("Inicializando gravador de arquivos...")
        self.text_writer = TextWriter(self.meeting_name, self.start_time_struct)
        
        self.set_status("Carregando modelo Whisper...")
        try:
            self.transcriber = Transcriber(
                model_size=self.model_size,
                language=self.language
            )
        except Exception as e:
            self.set_status(f"Falha ao carregar Whisper: {e}")
            self.is_recording = False
            return False
            
        # Start background transcription processing thread
        self.transcription_thread = threading.Thread(target=self._transcription_loop, daemon=True)
        self.transcription_thread.start()
        
        # Launch recorders
        self._start_recorders()
        
        self.set_status("Ouvindo")
        return True
        
    def _start_recorders(self):
        # 1. Microphone
        if not self.no_mic:
            try:
                if self.mic_name:
                    # Select specific mic by name substring
                    selected_mic = None
                    for m in sc.all_microphones():
                        if self.mic_name.lower() in m.name.lower():
                            selected_mic = m
                            break
                    if not selected_mic:
                        raise ValueError(f"Microfone '{self.mic_name}' não encontrado.")
                else:
                    selected_mic = sc.default_microphone()
                    
                self.mic_thread = AudioRecorderThread(
                    device=selected_mic,
                    source_name="Você",
                    sample_rate=16000,
                    chunk_size=480,
                    transcription_queue=self.transcription_queue,
                    meeting_start_time=self.meeting_start_time,
                    rms_callback=lambda rms: self._handle_rms("Você", rms)
                )
                self.mic_thread.start()
                logger.info(f"Microfone ativo: {selected_mic.name}")
            except Exception as e:
                logger.error(f"Não foi possível iniciar o microfone: {e}")
                
        # 2. Speaker (System Loopback)
        if not self.no_speaker:
            try:
                if self.speaker_name:
                    selected_spk = None
                    for s in sc.all_speakers():
                        if self.speaker_name.lower() in s.name.lower():
                            selected_spk = s
                            break
                    if not selected_spk:
                        raise ValueError(f"Saída de som '{self.speaker_name}' não encontrada.")
                else:
                    selected_spk = sc.default_speaker()
                    
                # Use soundcard's method to get a loopback recording device for this speaker
                loopback_device = sc.get_microphone(selected_spk.name, include_loopback=True)
                
                self.spk_thread = AudioRecorderThread(
                    device=loopback_device,
                    source_name="Sistema",
                    sample_rate=16000,
                    chunk_size=480,
                    transcription_queue=self.transcription_queue,
                    meeting_start_time=self.meeting_start_time,
                    rms_callback=lambda rms: self._handle_rms("Sistema", rms)
                )
                self.spk_thread.start()
                logger.info(f"Loopback ativo para: {selected_spk.name}")
            except Exception as e:
                logger.error(f"Não foi possível iniciar captura de som do sistema: {e}")
                
    def _handle_rms(self, source, rms):
        if self.on_rms and not self.is_paused:
            self.on_rms(source, rms)
            
    def _transcription_loop(self):
        while self.is_recording or not self.transcription_queue.empty():
            try:
                # Use timeout to verify shutdown conditions
                item = self.transcription_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            source = item["source"]
            start_time = item["start_time"]
            end_time = item["end_time"]
            audio = item["audio"]
            
            # Update status during transcription processing
            self.set_status("Transcrevendo")
            
            text = self.transcriber.transcribe(audio)
            
            if text and text.strip():
                # Write incrementally
                self.text_writer.append_event(source, start_time, end_time, text)
                
                # Store segment for final post-processing
                self.all_segments.append({
                    "source": source,
                    "timestamp": start_time,
                    "duration": end_time - start_time,
                    "text": text,
                    "audio": audio
                })
                
                if self.on_transcription:
                    self.on_transcription(source, start_time, end_time, text)
                    
            if self.is_recording and not self.is_paused:
                self.set_status("Ouvindo")
                
    def pause_meeting(self):
        """Pauses the recording by stopping the device recording threads."""
        if not self.is_recording or self.is_paused:
            return
            
        self.is_paused = True
        self.set_status("Pausando captura...")
        self._stop_recorders()
        self.set_status("Pausado")
        
    def resume_meeting(self):
        """Resumes the recording by restarting device recording threads."""
        if not self.is_recording or not self.is_paused:
            return
            
        self.is_paused = False
        self.set_status("Retomando captura...")
        self._start_recorders()
        self.set_status("Ouvindo")
        
    def _stop_recorders(self):
        # Stop mic recorder
        if self.mic_thread:
            self.mic_thread.stop()
            self.mic_thread.join()
            self.mic_thread = None
            
        # Stop speaker loopback recorder
        if self.spk_thread:
            self.spk_thread.stop()
            self.spk_thread.join()
            self.spk_thread = None
            
    def stop_meeting(self):
        """Stops the recording session, flushes VAD, clusters speakers, and post-processes transcripts."""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        self.set_status("Finalizando gravação...")
        
        # Stop devices (flushes remaining buffers into queue)
        self._stop_recorders()
        
        # Wait for queue to empty and transcriber thread to finish
        if self.transcription_thread:
            self.transcription_thread.join()
            self.transcription_thread = None
            
        self.set_status("Rodando diarização de voz...")
        # 1. Voice Diarization
        diarized_events = run_diarization(self.all_segments)
        self.text_writer.write_diarized(diarized_events)
        
        # 2. Ollama local LLM postprocessing
        final_folder = self.text_writer.folder_path
        if not self.no_postprocess:
            self.set_status("Contatando Ollama local...")
            model = get_ollama_model()
            if model:
                self.set_status("Refinando texto e criando sumário...")
                
                # Format diarized events for LLM
                transcript_text = ""
                for ev in diarized_events:
                    time_str = self.text_writer.format_timestamp(ev["timestamp"])
                    transcript_text += f"**[{ev['speaker_label']}]** ({time_str}):\n{ev['text']}\n\n"
                    
                # Prompts
                topic_prompt = f"""
Você é um assistente de IA para reuniões. Com base na transcrição abaixo, infira um título curto (1 a 4 palavras) em português que resuma o assunto principal da reunião.
Responda APENAS com o título curto, sem pontuação extra, introduções ou explicações.

Transcrição:
{transcript_text}
"""
                
                correct_prompt = f"""
Você é um revisor de texto especializado. Abaixo está a transcrição de uma reunião gerada por um sistema de reconhecimento de fala (ASR).
A transcrição pode conter erros gramaticais, palavras trocadas devido ao som parecido, nomes próprios incorretos e falta de pontuação.
Sua tarefa é corrigir e melhorar o texto mantendo o sentido original, os falantes e as falas intactas.
Escreva o texto revisado no mesmo formato markdown original (ex: **[usuario_1]** (00:12): texto).
Não adicione comentários seus, responda apenas com a transcrição revisada.

Transcrição original:
{transcript_text}
"""
                
                report_prompt = f"""
Você é um assistente executivo sênior. Com base na transcrição da reunião abaixo, gere um relatório profissional contendo:
1. **Resumo Executivo**: Um parágrafo resumindo o objetivo e as principais decisões da reunião.
2. **Pauta Inferida**: Tópicos discutidos detalhadamente.
3. **Ações e Follow-up**: Lista de tarefas, responsáveis e prazos mencionados na reunião.

Gere a saída formatada em Markdown elegante e profissional em português.

Transcrição da reunião:
{transcript_text}
"""
                
                topic = query_ollama(topic_prompt, model)
                revised = query_ollama(correct_prompt, model)
                report = query_ollama(report_prompt, model)
                
                self.text_writer.write_postprocessed(revised, report)
                
                if topic:
                    final_folder = self.text_writer.rename_folder_with_topic(topic)
            else:
                logger.info("Ollama indisponível ou nenhum modelo instalado. Pulando refinamento de IA.")
                
        self.set_status("Sessão finalizada com sucesso.")
        return final_folder
