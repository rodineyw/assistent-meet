import os
import logging
from faster_whisper import WhisperModel
from utils.app_paths import get_models_dir

logger = logging.getLogger("Transcriber")

class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8", cpu_threads=4, language="pt"):
        self.language = language
        
        # Check if local model directory contains files
        models_dir = get_models_dir()
        local_model_path = os.path.join(models_dir, f"whisper-{model_size}-pt-br")
        
        if os.path.exists(local_model_path) and os.listdir(local_model_path):
            logger.info(f"Carregando modelo Whisper local de: {local_model_path}")
            self.model_path = local_model_path
        else:
            logger.info(f"Carregando modelo Whisper '{model_size}' do cache/HuggingFace")
            self.model_path = model_size
            
        try:
            self.model = WhisperModel(
                self.model_path,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads
            )
            logger.info("Modelo Whisper inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar modelo Whisper: {e}")
            raise e
            
    def transcribe(self, audio_data):
        """
        Transcribes a float32 16kHz mono audio segment.
        Returns the transcription text.
        """
        if len(audio_data) == 0:
            return ""
            
        try:
            # We already run VAD ourselves, so we disable whisper's built-in VAD filter
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language,
                beam_size=3,
                temperature=0.0,
                condition_on_previous_text=False,
                without_timestamps=True,
                vad_filter=False
            )
            
            text_segments = [seg.text for seg in segments]
            transcription = "".join(text_segments).strip()
            return transcription
        except Exception as e:
            logger.error(f"Erro na inferência do Whisper: {e}")
            return ""

    def transcribe_file_iter(self, file_path, vad_filter=True):
        """
        Transcribes an audio or video file and yields timestamped segments.
        """
        try:
            segments, info = self.model.transcribe(
                file_path,
                language=self.language,
                beam_size=3,
                temperature=0.0,
                condition_on_previous_text=False,
                without_timestamps=False,
                vad_filter=vad_filter
            )

            for seg in segments:
                text = (seg.text or "").strip()
                if not text:
                    continue
                yield {
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": text,
                }
        except Exception as e:
            logger.error(f"Erro na transcrição do arquivo '{file_path}': {e}")
            raise
