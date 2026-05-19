import pyperclip
import logging

logger = logging.getLogger("Clipboard")

def copy_to_clipboard(text):
    """Copies text to system clipboard using pyperclip."""
    try:
        pyperclip.copy(text)
        logger.info("Texto copiado para a área de transferência com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Falha ao copiar para a área de transferência: {e}")
        return False
