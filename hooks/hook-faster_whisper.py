from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# `faster-whisper` needs the bundled Silero VAD ONNX asset for file-based
# transcription when `vad_filter=True`.
datas = collect_data_files("faster_whisper") + copy_metadata("faster-whisper")
