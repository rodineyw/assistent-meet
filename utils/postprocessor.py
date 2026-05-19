import httpx
import logging

logger = logging.getLogger("PostProcessor")

OLLAMA_URL = "http://localhost:11434"

def get_ollama_model(preferred_model="gemma4:latest"):
    """
    Checks if Ollama is running and returns the best available model.
    Falls back to first available model if preferred_model is missing.
    Returns None if Ollama is unreachable.
    """
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2.0)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            model_names = [m["name"] for m in models_data]
            
            if not model_names:
                logger.warning("Ollama está rodando, mas não possui nenhum modelo baixado/instalado.")
                return None
                
            if preferred_model in model_names:
                logger.info(f"Ollama modelo preferido encontrado: {preferred_model}")
                return preferred_model
                
            # Check for model name matches without tag
            pref_prefix = preferred_model.split(":")[0]
            for name in model_names:
                if name.startswith(pref_prefix):
                    logger.info(f"Ollama modelo compatível encontrado: {name}")
                    return name
                    
            # Fallback to the first available model
            fallback = model_names[0]
            logger.info(f"Modelo '{preferred_model}' não encontrado. Utilizando fallback: '{fallback}'")
            return fallback
    except Exception as e:
        logger.warning(f"Ollama não pôde ser contatado em {OLLAMA_URL}: {e}")
    return None

def query_ollama(prompt, model):
    """
    Sends a prompt to Ollama's generate API and returns the string response.
    Returns None if the request fails.
    """
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        logger.info(f"Enviando requisição ao Ollama usando o modelo '{model}'...")
        response = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60.0)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            logger.error(f"Erro na API do Ollama: Código HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Falha na comunicação com Ollama: {e}")
    return None
