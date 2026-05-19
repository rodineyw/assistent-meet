import time
import queue
import logging
import threading
import numpy as np
from utils.vad_detector import VADDetector

logger = logging.getLogger("AudioCapture")

class AudioRecorderThread(threading.Thread):
    def __init__(self, device, source_name, sample_rate=16000, chunk_size=480, 
                 transcription_queue=None, meeting_start_time=None, 
                 vad_mode=2, silence_timeout_s=0.8, max_segment_s=6.0, rms_callback=None):
        super().__init__(name=f"Recorder_{source_name}")
        self.device = device
        self.source_name = source_name
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.transcription_queue = transcription_queue
        self.meeting_start_time = meeting_start_time
        self.rms_callback = rms_callback
        self.running = False
        
        self.vad = VADDetector(
            sample_rate=sample_rate,
            mode=vad_mode,
            silence_timeout_s=silence_timeout_s,
            max_segment_s=max_segment_s
        )
        
        self.samples_recorded = 0
        self.speech_start_time = None
        
    def run(self):
        self.running = True
        logger.info(f"Iniciando gravação do dispositivo: {self.device.name}")
        
        try:
            with self.device.recorder(samplerate=self.sample_rate) as recorder:
                while self.running:
                    # Capture chunk of frames
                    data = recorder.record(numframes=self.chunk_size)
                    
                    # Convert to mono float32
                    if data.ndim > 1 and data.shape[1] > 1:
                        mono = np.mean(data, axis=1)
                    else:
                        mono = data.flatten()
                        
                    # Calculate real-time RMS for UI meters
                    if self.rms_callback:
                        rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) > 0 else 0.0
                        self.rms_callback(rms)
                        
                    # Timestamps relative to the start of recording
                    chunk_duration = len(mono) / self.sample_rate
                    chunk_start_time = self.samples_recorded / self.sample_rate
                    chunk_end_time = (self.samples_recorded + len(mono)) / self.sample_rate
                    self.samples_recorded += len(mono)
                    
                    # Process chunk through VAD state machine
                    was_speaking = self.vad.is_speaking
                    completed_segment = self.vad.process_chunk(mono)
                    
                    if not was_speaking and self.vad.is_speaking:
                        # Mark starting timestamp of speaking segment
                        self.speech_start_time = chunk_start_time
                        
                    if completed_segment is not None:
                        segment_audio = completed_segment["audio"]
                        segment_duration = len(segment_audio) / self.sample_rate
                        if completed_segment["continues"]:
                            actual_end_time = (self.speech_start_time or 0.0) + segment_duration
                        else:
                            silence_duration = self.vad.silence_timeout_frames * (self.vad.frame_duration_ms / 1000.0)
                            actual_end_time = max(self.speech_start_time or 0.0, chunk_end_time - silence_duration)
                        
                        if self.transcription_queue:
                            self.transcription_queue.put({
                                "source": self.source_name,
                                "start_time": self.speech_start_time,
                                "end_time": actual_end_time,
                                "audio": segment_audio
                            })
                        if completed_segment["continues"]:
                            self.speech_start_time = actual_end_time
                        else:
                            self.speech_start_time = None
                        
        except Exception as e:
            logger.error(f"Erro na thread de gravação [{self.source_name}]: {e}")
        finally:
            logger.info(f"Thread de gravação [{self.source_name}] finalizada.")
            
    def stop(self):
        self.running = False
        # Flush webrtcvad buffers
        remaining = self.vad.flush()
        if remaining is not None and self.speech_start_time is not None:
            segment_audio = remaining["audio"]
            actual_end_time = self.samples_recorded / self.sample_rate
            if self.transcription_queue:
                self.transcription_queue.put({
                    "source": self.source_name,
                    "start_time": self.speech_start_time,
                    "end_time": actual_end_time,
                    "audio": segment_audio
                })
