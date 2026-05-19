import logging
import webrtcvad
import numpy as np

logger = logging.getLogger("VADDetector")

class VADDetector:
    def __init__(self, sample_rate=16000, frame_duration_ms=30, mode=2, 
                 silence_timeout_s=0.8, speech_trigger_s=0.2, max_segment_s=6.0):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.vad = webrtcvad.Vad(mode)
        
        # Calculate sizes in samples
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.silence_timeout_frames = int(silence_timeout_s * 1000 / frame_duration_ms)
        self.speech_trigger_frames = int(speech_trigger_s * 1000 / frame_duration_ms)
        self.max_segment_frames = max(1, int(max_segment_s * 1000 / frame_duration_ms))
        
        self.is_speaking = False
        self.speech_buffer = []
        
        self.consecutive_speech_frames = 0
        self.consecutive_silent_frames = 0
        
    def process_chunk(self, float32_mono_chunk):
        """
        Processes a block of float32 samples.
        Splits into 30ms frames and runs VAD.
        Returns a dict with the completed speech segment and whether the speaker
        should still be considered mid-utterance, or None.
        """
        # Convert float32 [-1, 1] to int16
        int16_chunk = (float32_mono_chunk * 32767.0).clip(-32768, 32767).astype(np.int16)
        
        completed_segment = None
        
        # Split into frame_size chunks (webrtcvad expects exact frame size)
        # Typically chunk size is 480, which matches exactly frame_size.
        # But if we get a different size, we slice it.
        offset = 0
        while offset + self.frame_size <= len(int16_chunk):
            frame_int16 = int16_chunk[offset:offset+self.frame_size]
            frame_float32 = float32_mono_chunk[offset:offset+self.frame_size]
            offset += self.frame_size
            
            pcm_bytes = frame_int16.tobytes()
            try:
                is_speech = self.vad.is_speech(pcm_bytes, self.sample_rate)
            except Exception as e:
                logger.error(f"VAD is_speech error: {e}")
                is_speech = False
                
            if is_speech:
                self.consecutive_speech_frames += 1
                self.consecutive_silent_frames = 0
                
                if not self.is_speaking:
                    if self.consecutive_speech_frames >= self.speech_trigger_frames:
                        self.is_speaking = True
                        # Triggered speech!
                
                if self.is_speaking:
                    self.speech_buffer.append(frame_float32)
                    if len(self.speech_buffer) >= self.max_segment_frames:
                        completed_segment = {
                            "audio": np.concatenate(self.speech_buffer),
                            "continues": True
                        }
                        self.speech_buffer = []
                        self.consecutive_silent_frames = 0
                        break
            else:
                self.consecutive_silent_frames += 1
                self.consecutive_speech_frames = 0
                
                if self.is_speaking:
                    self.speech_buffer.append(frame_float32)
                    if self.consecutive_silent_frames >= self.silence_timeout_frames:
                        # Silence timeout! Yield the accumulated speech minus trailing silence
                        self.is_speaking = False
                        n_silent = self.silence_timeout_frames
                        
                        if len(self.speech_buffer) > n_silent:
                            segment_chunks = self.speech_buffer[:-n_silent]
                        else:
                            segment_chunks = self.speech_buffer
                            
                        if segment_chunks:
                            completed_segment = {
                                "audio": np.concatenate(segment_chunks),
                                "continues": False
                            }
                            
                        self.speech_buffer = []
                        self.consecutive_silent_frames = 0
                        break # Stop processing further frames in this chunk to prevent multiple yields
                        
        return completed_segment
        
    def flush(self):
        """Flushes any remaining speech buffer, returning a completed segment if any."""
        if self.is_speaking and self.speech_buffer:
            # Strip trailing silence up to current consecutive silent frames
            n_silent = self.consecutive_silent_frames
            if n_silent > 0 and len(self.speech_buffer) > n_silent:
                segment_chunks = self.speech_buffer[:-n_silent]
            else:
                segment_chunks = self.speech_buffer
                
            self.is_speaking = False
            self.speech_buffer = []
            self.consecutive_silent_frames = 0
            self.consecutive_speech_frames = 0
            
            if segment_chunks:
                return {
                    "audio": np.concatenate(segment_chunks),
                    "continues": False
                }
        return None

def extract_voice_signature(audio_data, sample_rate=16000):
    """
    Extracts a 20-dimensional log-frequency power spectrum timbre signature
    from a float32 audio segment. Returns a normalized 1D numpy array.
    """
    if len(audio_data) < 160: # Too short
        return np.zeros(20)
        
    try:
        # Compute magnitude spectrum
        fft_vals = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), 1.0 / sample_rate)
        
        # Log-spaced frequency bands in human speech frequency range (100Hz - 4000Hz)
        bands = np.logspace(np.log10(100), np.log10(4000), 21)
        features = []
        for i in range(20):
            low, high = bands[i], bands[i+1]
            idx = (freqs >= low) & (freqs < high)
            if np.any(idx):
                features.append(np.mean(fft_vals[idx]))
            else:
                features.append(0.0)
                
        feat_arr = np.array(features)
        # Normalize
        norm = np.linalg.norm(feat_arr)
        if norm > 0:
            feat_arr /= norm
        return feat_arr
    except Exception as e:
        logger.error(f"Erro ao extrair assinatura de voz: {e}")
        return np.zeros(20)

def cluster_segments(signatures, distance_threshold=0.3):
    """
    Performs UPGMA Hierarchical Agglomerative Clustering on timbre signatures
    using cosine distance. Returns a list of cluster labels (0, 1, 2, ...).
    """
    n = len(signatures)
    if n == 0:
        return []
        
    # Map index to list of indices in that cluster
    clusters = {i: [i] for i in range(n)}
    
    # Distance cache can be computed on the fly or stored
    while len(clusters) > 1:
        min_dist = float('inf')
        best_pair = None
        
        keys = list(clusters.keys())
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                c_a = keys[i]
                c_b = keys[j]
                
                # Average Linkage: average cosine distance between all pairs in the two clusters
                dists = []
                for elem_a in clusters[c_a]:
                    for elem_b in clusters[c_b]:
                        # Cosine distance: 1.0 - cosine_similarity (dot product of normalized vectors)
                        d = 1.0 - np.dot(signatures[elem_a], signatures[elem_b])
                        dists.append(d)
                        
                avg_dist = np.mean(dists)
                if avg_dist < min_dist:
                    min_dist = avg_dist
                    best_pair = (c_a, c_b)
                    
        if best_pair is not None and min_dist < distance_threshold:
            c_keep, c_merge = best_pair
            # Merge clusters
            clusters[c_keep].extend(clusters[c_merge])
            del clusters[c_merge]
        else:
            # Stopping criterion met (closest distance is above threshold)
            break
            
    # Assign labels
    labels = [0] * n
    for cluster_id, (old_key, indices) in enumerate(clusters.items()):
        for idx in indices:
            labels[idx] = cluster_id
            
    return labels

def run_diarization(segments):
    """
    Separates user (Você) from system (Sistema) segments.
    Keeps user as 'usuario_1' and clusters system loopback into 'usuario_2', 'usuario_3', etc.
    """
    if not segments:
        return []
        
    mic_segments = []
    spk_segments = []
    
    for i, seg in enumerate(segments):
        if seg["source"] == "Você":
            mic_segments.append((i, seg))
        else:
            spk_segments.append((i, seg))
            
    diarized_events = [None] * len(segments)
    
    # Label microphone segments as "usuario_1" (Você)
    for idx, seg in mic_segments:
        diarized_events[idx] = {
            "timestamp": seg["timestamp"],
            "duration": seg["duration"],
            "text": seg["text"],
            "speaker_label": "usuario_1"
        }
        
    # Cluster loopback segments
    if spk_segments:
        signatures = []
        valid_spk_segments = []
        
        for idx, seg in spk_segments:
            sig = extract_voice_signature(seg["audio"])
            if np.any(sig):
                signatures.append(sig)
                valid_spk_segments.append((idx, seg))
            else:
                # Fallback for silent/invalid segments
                diarized_events[idx] = {
                    "timestamp": seg["timestamp"],
                    "duration": seg["duration"],
                    "text": seg["text"],
                    "speaker_label": "usuario_2"
                }
                
        if signatures:
            labels = cluster_segments(signatures)
            for (idx, seg), label in zip(valid_spk_segments, labels):
                # Map cluster 0 -> usuario_2, 1 -> usuario_3, ...
                diarized_events[idx] = {
                    "timestamp": seg["timestamp"],
                    "duration": seg["duration"],
                    "text": seg["text"],
                    "speaker_label": f"usuario_{label + 2}"
                }
        else:
            # If no signatures could be extracted, group all as usuario_2
            for idx, seg in spk_segments:
                if diarized_events[idx] is None:
                    diarized_events[idx] = {
                        "timestamp": seg["timestamp"],
                        "duration": seg["duration"],
                        "text": seg["text"],
                        "speaker_label": "usuario_2"
                    }
                    
    # Double check to prevent Nones
    for i in range(len(diarized_events)):
        if diarized_events[i] is None:
            diarized_events[i] = {
                "timestamp": segments[i]["timestamp"],
                "duration": segments[i]["duration"],
                "text": segments[i]["text"],
                "speaker_label": "usuario_1" if segments[i]["source"] == "Você" else "usuario_2"
            }
            
    return diarized_events
