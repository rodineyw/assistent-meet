import os
import logging
from contextlib import contextmanager

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from faster_whisper.utils import download_model

from utils.app_paths import get_bundled_models_dir, get_models_dir

logger = logging.getLogger("Transcriber")
REQUIRED_MODEL_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")


@contextmanager
def suppress_stderr():
    """Temporarily redirects process stderr to os.devnull for noisy native libraries."""
    stderr_fd = None
    devnull_fd = None

    try:
        stderr_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)
        yield
    finally:
        if stderr_fd is not None:
            os.dup2(stderr_fd, 2)
            os.close(stderr_fd)
        if devnull_fd is not None:
            os.close(devnull_fd)

class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8", cpu_threads=4, language="pt"):
        self.language = language

        self.model_size = model_size
        self.model_path = self._resolve_model_path(model_size)
            
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

    def _get_local_model_path(self, model_size):
        return os.path.join(get_models_dir(), f"whisper-{model_size}-pt-br")

    def _get_bundled_model_path(self, model_size):
        return os.path.join(get_bundled_models_dir(), f"whisper-{model_size}-pt-br")

    def _is_complete_model_dir(self, path):
        if not os.path.isdir(path):
            return False

        for filename in REQUIRED_MODEL_FILES:
            file_path = os.path.join(path, filename)
            if not os.path.isfile(file_path):
                return False
            if os.path.getsize(file_path) <= 0:
                return False
        return True

    def _ensure_local_model_copy(self, source_path, target_path):
        os.makedirs(target_path, exist_ok=True)
        for filename in REQUIRED_MODEL_FILES:
            source_file = os.path.join(source_path, filename)
            target_file = os.path.join(target_path, filename)
            if not os.path.exists(source_file):
                raise FileNotFoundError(f"Arquivo do modelo ausente: {source_file}")
            with open(source_file, "rb") as src, open(target_file, "wb") as dst:
                dst.write(src.read())

    def _download_model_to_local_dir(self, model_size, local_model_path):
        logger.info(f"Preparando modelo Whisper '{model_size}' em: {local_model_path}")

        try:
            cached_snapshot_path = download_model(model_size, local_files_only=True)
            if self._is_complete_model_dir(cached_snapshot_path):
                self._ensure_local_model_copy(cached_snapshot_path, local_model_path)
                logger.info("Modelo Whisper copiado do cache local do Hugging Face.")
                return
        except Exception as exc:
            logger.info(f"Cache local do Hugging Face indisponivel para o modelo '{model_size}': {exc}")

        download_model(model_size, output_dir=local_model_path, local_files_only=False)
        if not self._is_complete_model_dir(local_model_path):
            raise RuntimeError(
                f"O download do modelo Whisper '{model_size}' terminou sem gerar todos os arquivos esperados."
            )
        logger.info("Modelo Whisper baixado e salvo na pasta local do aplicativo.")

    def _resolve_model_path(self, model_size):
        local_model_path = self._get_local_model_path(model_size)
        if self._is_complete_model_dir(local_model_path):
            logger.info(f"Carregando modelo Whisper local de: {local_model_path}")
            return local_model_path

        bundled_model_path = self._get_bundled_model_path(model_size)
        if self._is_complete_model_dir(bundled_model_path):
            logger.info(f"Copiando modelo Whisper empacotado para: {local_model_path}")
            self._ensure_local_model_copy(bundled_model_path, local_model_path)
            return local_model_path

        logger.info(
            f"Modelo Whisper local nao encontrado ou incompleto. "
            f"Tentando preparar '{model_size}' em {local_model_path}."
        )
        self._download_model_to_local_dir(model_size, local_model_path)
        return local_model_path
            
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
            # PyAV/FFmpeg may emit repetitive COM initialization warnings on Windows
            # when probing media containers. We silence stderr here and still surface
            # actual failures through Python exceptions below.
            with suppress_stderr():
                audio_data = decode_audio(file_path, sampling_rate=16000)

            try:
                segments, info = self.model.transcribe(
                    audio_data,
                    language=self.language,
                    beam_size=3,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    without_timestamps=False,
                    vad_filter=vad_filter
                )
            except Exception as exc:
                should_retry_without_vad = vad_filter and (
                    "silero_vad_v6.onnx" in str(exc) or
                    "NO_SUCHFILE" in str(exc).upper()
                )
                if not should_retry_without_vad:
                    raise

                logger.warning(
                    "Falha ao carregar o VAD empacotado do faster-whisper. "
                    "A transcricao do arquivo sera refeita sem VAD interno."
                )
                segments, info = self.model.transcribe(
                    audio_data,
                    language=self.language,
                    beam_size=3,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    without_timestamps=False,
                    vad_filter=False
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
