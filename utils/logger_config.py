import logging
import os
import sys
from utils.app_paths import get_logs_dir

def setup_logging():
    """Sets up global logging configuration with UTF-8 encoding."""
    logs_dir = get_logs_dir()
    log_file = os.path.join(logs_dir, "app.log")
    
    # Configure formatting
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if root_logger.handlers:
        return
        
    # UTF-8 File Handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Erro ao criar arquivo de log: {e}", file=sys.stderr)
        
    # Stream Handler (console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
