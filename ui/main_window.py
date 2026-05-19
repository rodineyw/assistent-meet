import os
import math
import logging
import subprocess
import threading
import ctypes
from PySide6.QtCore import Qt, QPoint, QTimer, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPlainTextEdit, QPushButton, QComboBox, QLineEdit, QFrame, 
    QMessageBox, QDialog, QApplication, QSizePolicy
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextCursor, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
import soundcard as sc

from utils.meeting_manager import MeetingManager
from utils.app_info import APP_ID, APP_NAME
from utils.clipboard import copy_to_clipboard
from utils.app_paths import get_app_icon_path, get_transcripts_dir, get_ui_asset_path

logger = logging.getLogger("MainWindow")

# Bridge QObject to dispatch background thread events safely to the main GUI thread
class RecorderSignalsBridge(QObject):
    transcription_received = Signal(str, float, float, str)  # source, start_time, end_time, text
    status_changed = Signal(str)
    rms_received = Signal(str, float)                        # source, rms_value
    meeting_stopped = Signal(object)                         # folder path or None


def load_app_icon():
    """Loads the application icon from the bundled UI assets."""
    icon_path = get_app_icon_path()
    if not icon_path:
        return QIcon()
    return QIcon(icon_path)


def render_logo_pixmap(size=32):
    """Renders the SVG logo into a pixmap for the header."""
    icon_path = get_app_icon_path()
    if not icon_path or not icon_path.lower().endswith(".svg"):
        return QPixmap()

    renderer = QSvgRenderer(icon_path)
    if not renderer.isValid():
        return QPixmap()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class MiniWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rms = 0.0
        self.phase = 0.0
        self.setMinimumWidth(80)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)  # ~33 FPS
        
    def set_rms(self, rms):
        self.rms = rms
        
    def update_wave(self):
        self.phase += 0.2
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        cy = h / 2.0
        
        # Timbre-responsive amplitude calculation
        amplitude = max(2.0, self.rms * 50.0)
        amplitude = min(amplitude, cy - 2.0)
        
        # Layer 1 (Indigo)
        pen1 = QPen(QColor(99, 102, 241, 100), 1.5)
        painter.setPen(pen1)
        points1 = []
        for x in range(0, w, 2):
            y = cy + amplitude * 0.6 * math.sin(x * 0.1 - self.phase)
            points1.append(QPoint(x, int(y)))
        for i in range(len(points1) - 1):
            painter.drawLine(points1[i], points1[i+1])
            
        # Layer 2 (Violet)
        pen2 = QPen(QColor(168, 85, 247, 220), 2.0)
        painter.setPen(pen2)
        points2 = []
        for x in range(0, w, 2):
            y = cy + amplitude * math.sin(x * 0.15 + self.phase)
            points2.append(QPoint(x, int(y)))
        for i in range(len(points2) - 1):
            painter.drawLine(points2[i], points2[i+1])


class FloatingWaveform(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(200, 50)
        self.drag_position = QPoint()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        self.label = QLabel("Ouvindo", self)
        self.label.setStyleSheet("color: #a855f7; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 11px;")
        layout.addWidget(self.label)
        
        self.wave = MiniWaveWidget(self)
        layout.addWidget(self.wave)
        
    def set_rms(self, rms):
        self.wave.set_rms(rms)
        
    def set_status(self, status):
        self.label.setText(status)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Glassmorphism capsule background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(18, 16, 22, 230)))
        painter.drawRoundedRect(self.rect(), 25, 25)
        
        # Gradient border
        pen = QPen(QColor(139, 92, 246, 180), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 24, 24)


class BigWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mic_rms = 0.0
        self.spk_rms = 0.0
        self.phase = 0.0
        self.setMinimumHeight(65)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)
        
    def set_rms(self, mic_rms, spk_rms):
        self.mic_rms = mic_rms
        self.spk_rms = spk_rms
        
    def update_wave(self):
        self.phase += 0.15
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        cy = h / 2.0
        
        # Dark visualizer background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(18, 16, 22, 120)))
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        mic_amp = min(max(2.0, self.mic_rms * 120.0), cy - 5.0)
        spk_amp = min(max(2.0, self.spk_rms * 120.0), cy - 5.0)
        
        # Loopback wave (Indigo)
        pen_spk = QPen(QColor(79, 70, 229, 130), 1.5)
        painter.setPen(pen_spk)
        points_spk = []
        for x in range(0, w, 4):
            y = cy + spk_amp * math.sin(x * 0.02 - self.phase)
            points_spk.append(QPoint(x, int(y)))
        for i in range(len(points_spk) - 1):
            painter.drawLine(points_spk[i], points_spk[i+1])
            
        # Microphone wave (Violet)
        pen_mic = QPen(QColor(139, 92, 246, 190), 2.0)
        painter.setPen(pen_mic)
        points_mic = []
        for x in range(0, w, 4):
            y = cy + mic_amp * math.sin(x * 0.035 + self.phase)
            points_mic.append(QPoint(x, int(y)))
        for i in range(len(points_mic) - 1):
            painter.drawLine(points_mic[i], points_mic[i+1])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Assistente Meet — Transcritor Local")
        self.resize(800, 600)
        
        self.manager = None
        self.last_folder_path = None
        
        # Signals bridge
        self.bridge = RecorderSignalsBridge()
        self.bridge.transcription_received.connect(self._on_transcription_received)
        self.bridge.status_changed.connect(self._on_status_changed)
        self.bridge.rms_received.connect(self._on_rms_received)
        self.bridge.meeting_stopped.connect(self._on_meeting_stopped)
        
        # Floating window
        self.floating_widget = FloatingWaveform()
        self._apply_branding()
        
        # Load style sheet
        self._load_stylesheet()
        
        # Initialize UI components
        self._init_ui()
        
    def _load_stylesheet(self):
        qss_path = get_ui_asset_path("style.qss")
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                logger.error(f"Erro ao carregar QSS: {e}")

    def _apply_branding(self):
        app_icon = load_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
            self.floating_widget.setWindowIcon(app_icon)
                
    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header Layout
        header_layout = QHBoxLayout()

        logo_label = QLabel(self)
        logo_pixmap = render_logo_pixmap(32)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(32, 32)
            header_layout.addWidget(logo_label)
        
        title_label = QLabel("Assistente Meet", self)
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        
        self.status_badge = QLabel("Inativo", self)
        self.status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.status_badge)
        
        header_layout.addStretch()
        
        self.btn_toggle_float = QPushButton("Visualizador Flutuante", self)
        self.btn_toggle_float.setCheckable(True)
        self.btn_toggle_float.clicked.connect(self._toggle_floating_view)
        header_layout.addWidget(self.btn_toggle_float)
        
        main_layout.addLayout(header_layout)
        
        # Setup Card (Visible before recording)
        self.setup_card = QFrame(self)
        self.setup_card.setObjectName("controlCard")
        setup_layout = QVBoxLayout(self.setup_card)
        setup_layout.setContentsMargins(15, 15, 15, 15)
        setup_layout.setSpacing(12)
        
        # Line 1: Meeting name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome da Reunião:", self))
        self.input_meeting_name = QLineEdit("daily", self)
        name_layout.addWidget(self.input_meeting_name)
        setup_layout.addLayout(name_layout)
        
        # Line 2: Audio Devices
        devices_layout = QHBoxLayout()
        
        devices_layout.addWidget(QLabel("Microfone:", self))
        self.combo_mic = QComboBox(self)
        devices_layout.addWidget(self.combo_mic)
        
        devices_layout.addWidget(QLabel("Saída de Áudio:", self))
        self.combo_speaker = QComboBox(self)
        devices_layout.addWidget(self.combo_speaker)
        
        setup_layout.addLayout(devices_layout)
        
        # Line 3: Whisper Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Modelo Whisper (Offline):", self))
        self.combo_model = QComboBox(self)
        self.combo_model.addItems(["tiny", "base", "small", "medium"])
        self.combo_model.setCurrentText("small")
        model_layout.addWidget(self.combo_model)
        model_layout.addStretch()
        
        setup_layout.addLayout(model_layout)
        main_layout.addWidget(self.setup_card)
        
        # Populate Audio Devices
        self._populate_devices()
        
        # Visualizer Wave Widget
        self.big_wave = BigWaveWidget(self)
        main_layout.addWidget(self.big_wave)
        
        # Text Area for Real-time Transcripts
        self.transcript_area = QPlainTextEdit(self)
        self.transcript_area.setReadOnly(True)
        self.transcript_area.setPlaceholderText("A transcrição da reunião aparecerá aqui em tempo real...")
        main_layout.addWidget(self.transcript_area)
        
        # Bottom controls Card
        self.control_card = QFrame(self)
        self.control_card.setObjectName("controlCard")
        control_layout = QHBoxLayout(self.control_card)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(10)
        
        self.btn_record = QPushButton("Iniciar Reunião", self)
        self.btn_record.setObjectName("recordButton")
        self.btn_record.clicked.connect(self._on_record_clicked)
        control_layout.addWidget(self.btn_record)
        
        self.btn_stop = QPushButton("Encerrar Reunião", self)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self.btn_stop)
        
        control_layout.addStretch()
        
        self.btn_copy = QPushButton("Copiar Texto", self)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        control_layout.addWidget(self.btn_copy)
        
        self.btn_notepad = QPushButton("Abrir Bloco de Notas", self)
        self.btn_notepad.clicked.connect(self._on_notepad_clicked)
        control_layout.addWidget(self.btn_notepad)
        
        self.btn_folder = QPushButton("Abrir Pasta", self)
        self.btn_folder.clicked.connect(self._on_folder_clicked)
        control_layout.addWidget(self.btn_folder)
        
        main_layout.addWidget(self.control_card)
        
    def _populate_devices(self):
        # Microphones
        self.combo_mic.addItem("Padrão do Sistema", None)
        try:
            for m in sc.all_microphones():
                self.combo_mic.addItem(m.name, m.name)
        except Exception as e:
            logger.error(f"Erro ao buscar microfones: {e}")
            
        # Speakers
        self.combo_speaker.addItem("Padrão do Sistema", None)
        try:
            for s in sc.all_speakers():
                self.combo_speaker.addItem(s.name, s.name)
        except Exception as e:
            logger.error(f"Erro ao buscar dispositivos de saída: {e}")
            
    def _toggle_floating_view(self):
        if self.btn_toggle_float.isChecked():
            # Align next to the main window
            rect = self.geometry()
            self.floating_widget.move(rect.right() - 210, rect.top() + 50)
            self.floating_widget.show()
        else:
            self.floating_widget.hide()
            
    def _on_record_clicked(self):
        if self.manager is None:
            # Start Recording
            meeting_name = self.input_meeting_name.text().strip() or "reuniao"
            model_size = self.combo_model.currentText()
            mic_name = self.combo_mic.currentData()
            speaker_name = self.combo_speaker.currentData()
            
            self.transcript_area.clear()
            self.setup_card.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_record.setProperty("recording", "true")
            self.btn_record.setStyle(self.btn_record.style()) # Refresh styling
            
            # Instantiate manager with callbacks mapping to thread-safe bridge signals
            self.manager = MeetingManager(
                meeting_name=meeting_name,
                model_size=model_size,
                mic_name=mic_name,
                speaker_name=speaker_name,
                on_transcription=lambda src, st, et, txt: self.bridge.transcription_received.emit(src, st, et, txt),
                on_status=lambda stat: self.bridge.status_changed.emit(stat),
                on_rms=lambda src, val: self.bridge.rms_received.emit(src, val)
            )
            
            # Start background session
            threading.Thread(target=self.manager.start_meeting, daemon=True).start()
            self.btn_record.setText("Pausar")
        else:
            # Handle Pause / Resume toggle
            if self.manager.is_paused:
                self.manager.resume_meeting()
                self.btn_record.setText("Pausar")
            else:
                self.manager.pause_meeting()
                self.btn_record.setText("Retomar")
                
    def _on_stop_clicked(self):
        if self.manager is not None:
            self.btn_record.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.status_badge.setText("Processando...")
            
            # Stop and finalize in a background thread to prevent GUI freezing
            def run_stop():
                folder = self.manager.stop_meeting()
                self.bridge.meeting_stopped.emit(folder)
                
            threading.Thread(target=run_stop, daemon=True).start()
            
    @Slot(object)
    def _on_meeting_stopped(self, folder):
        self.last_folder_path = folder
        self.manager = None
        
        self.setup_card.setEnabled(True)
        self.btn_record.setEnabled(True)
        self.btn_record.setText("Iniciar Reunião")
        self.btn_record.setProperty("recording", "false")
        self.btn_record.setStyle(self.btn_record.style())
        
        self.status_badge.setText("Inativo")
        
        # Reset waves
        self.big_wave.set_rms(0.0, 0.0)
        self.floating_widget.set_rms(0.0)
        
        QMessageBox.information(
            self,
            "Reunião Finalizada",
            f"A gravação foi concluída e os arquivos de transcrição foram salvos em:\n{folder}"
        )
        
    def _on_copy_clicked(self):
        text = self.transcript_area.toPlainText().strip()
        if text:
            if copy_to_clipboard(text):
                QMessageBox.information(self, "Copiado", "A transcrição foi copiada para a área de transferência.")
        else:
            QMessageBox.warning(self, "Aviso", "Não há texto para copiar.")
            
    def _on_notepad_clicked(self):
        # Open the transcript file in Notepad
        path_to_open = None
        if self.manager and self.manager.text_writer:
            path_to_open = self.manager.text_writer.transcript_path
        elif self.last_folder_path:
            # Check for different files in order of preference
            options = ["transcript_diarizado.md", "transcript.md"]
            for opt in options:
                test_path = os.path.join(self.last_folder_path, opt)
                if os.path.exists(test_path):
                    path_to_open = test_path
                    break
                    
        if path_to_open and os.path.exists(path_to_open):
            try:
                subprocess.Popen(["notepad.exe", path_to_open])
            except Exception as e:
                logger.error(f"Erro ao abrir Bloco de Notas: {e}")
        else:
            QMessageBox.warning(self, "Não disponível", "Nenhum arquivo de transcrição disponível no momento.")
            
    def _on_folder_clicked(self):
        folder_to_open = self.last_folder_path or get_transcripts_dir()
        if os.path.exists(folder_to_open):
            try:
                os.startfile(folder_to_open)
            except Exception as e:
                logger.error(f"Erro ao abrir pasta: {e}")
        else:
            QMessageBox.warning(self, "Não disponível", "A pasta de transcrições não foi encontrada.")
            
    # Bridge Slots (running on UI thread)
    @Slot(str, float, float, str)
    def _on_transcription_received(self, source, start_time, end_time, text):
        time_str = ""
        if self.manager and self.manager.text_writer:
            time_str = self.manager.text_writer.format_timestamp(start_time)
            
        formatted_entry = f"[{source}] ({time_str}): {text}\n"
        self.transcript_area.appendPlainText(formatted_entry)
        self.transcript_area.moveCursor(QTextCursor.End)
        
    @Slot(str)
    def _on_status_changed(self, status):
        self.status_badge.setText(status)
        self.floating_widget.set_status(status)
        
    @Slot(str, float)
    def _on_rms_received(self, source, rms):
        if source == "Você":
            self.big_wave.set_rms(rms, self.big_wave.spk_rms)
            # The floating widget displays mic level as priority
            self.floating_widget.set_rms(max(rms, self.big_wave.spk_rms))
        else:
            self.big_wave.set_rms(self.big_wave.mic_rms, rms)
            self.floating_widget.set_rms(max(rms, self.big_wave.mic_rms))
            
    def closeEvent(self, event):
        # Shut down floating widget and meeting manager
        self.floating_widget.close()
        if self.manager:
            self.manager.stop_meeting()
        event.accept()


def run_gui():
    import sys

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception as e:
            logger.warning(f"Não foi possível definir o AppUserModelID do Windows: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)

    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
