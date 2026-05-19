rod, a melhor estratégia é **não tentar clonar o Superwhisper inteiro no início**. O MVP correto é: **app Windows leve, offline, PT-BR, abre e já começa a ouvir, transcreve por blocos de fala, salva em `.txt` e mantém uma interface simples.**

## Veredito técnico

| Opção                                 | Peso de acerto | Decisão                                                                                                             |
| ------------------------------------- | -------------: | ------------------------------------------------------------------------------------------------------------------- |
| **Python + faster-whisper + PySide6** |        **90%** | Melhor para MVP rápido, offline, boa precisão e interface elegante.                                                 |
| **C++ + whisper.cpp**                 |        **82%** | Mais leve e performático, mas mais trabalhoso para criar app completo.                                              |
| **Vosk PT-BR**                        |        **55%** | Muito leve, mas a precisão em PT-BR tende a ser pior. O modelo small PT tem WER alto em alguns benchmarks oficiais. |
| **Electron + Whisper local**          |        **45%** | Interface bonita, mas pesado demais para o objetivo.                                                                |
| **API online**                        |         **0%** | Fora do requisito: precisa ser 100% offline.                                                                        |

Minha escolha: **Python + faster-whisper no MVP**, com possibilidade futura de trocar o motor para **whisper.cpp** se quisermos reduzir ainda mais consumo.

---

# Stack recomendada

## Motor de transcrição

### `faster-whisper`

Motivo: é uma implementação do Whisper usando CTranslate2. O projeto informa ser até **4x mais rápido que o whisper original**, mantendo a mesma precisão e usando menos memória, com suporte a quantização em 8 bits. ([GitHub][1])

O CTranslate2 usa otimizações como **quantização de pesos, fusão de camadas e execução eficiente em CPU/GPU**, o que ajuda no nosso objetivo de baixo impacto no sistema. ([GitHub][2])

## Interface

### `PySide6`

Motivo: é o binding oficial do Qt para Python e dá acesso ao framework Qt 6, bom para criar interface desktop nativa e elegante. ([PyPI][3])

## Captura de áudio

### `sounddevice`

Captura microfone em tempo real com baixo overhead.

## Detecção de fala

### `webrtcvad` ou VAD interno do faster-whisper

A ideia é **não transcrever silêncio**. Isso reduz CPU, RAM e melhora a experiência.

## Empacotamento

### `PyInstaller`

O PyInstaller empacota o app Python e suas dependências para o usuário executar sem instalar Python manualmente. ([pyinstaller.org][4])

---

# Decisão sobre modelo

| Modelo              | Peso de acerto | Uso recomendado                                                    |
| ------------------- | -------------: | ------------------------------------------------------------------ |
| `small` com `int8`  |        **88%** | Melhor padrão inicial: bom equilíbrio entre precisão e velocidade. |
| `base` com `int8`   |            72% | Mais leve, mas pode errar mais em PT-BR.                           |
| `medium` com `int8` |            80% | Mais preciso, porém mais pesado. Bom como modo “Alta precisão”.    |
| `tiny`              |            45% | Muito rápido, mas precisão fraca para produto sério.               |

Configuração inicial recomendada:

```txt
Modelo padrão: small
Idioma fixo: pt
Compute type: int8
Modo: CPU primeiro
VAD: ativado
Transcrição: por blocos de fala
```

O Whisper original foi treinado em grande volume de dados multilíngues e é conhecido por robustez com sotaques, ruído e linguagem técnica. ([OpenAI][5])

---

# Arquitetura do app

```txt
app/
├── main.py
├── utils/
│   ├── logger_config.py
│   ├── audio_capture.py
│   ├── vad_detector.py
│   ├── transcriber.py
│   ├── text_writer.py
│   ├── clipboard.py
│   └── app_paths.py
├── ui/
│   ├── main_window.py
│   └── style.qss
├── models/
│   └── whisper-small-pt-br/
├── logs/
│   └── app.log
├── transcricoes/
│   └── transcricao_2026-05-19_1030.txt
├── pyproject.toml
└── README.md
```

## Responsabilidade de cada parte

| Arquivo            | Função                                  |
| ------------------ | --------------------------------------- |
| `main.py`          | Só inicializa o app. Enxuto.            |
| `logger_config.py` | Configura logging UTF-8.                |
| `audio_capture.py` | Captura áudio do microfone.             |
| `vad_detector.py`  | Detecta quando há fala real.            |
| `transcriber.py`   | Executa o modelo offline.               |
| `text_writer.py`   | Salva transcrição em `.txt`.            |
| `clipboard.py`     | Copia texto para área de transferência. |
| `main_window.py`   | Interface gráfica.                      |

---

# Fluxo do usuário

```txt
1. Usuário abre o app.
2. App carrega o modelo local.
3. App começa a ouvir automaticamente.
4. Quando detecta fala, grava um bloco temporário.
5. Ao detectar pausa, envia o bloco para transcrição.
6. Texto aparece na interface.
7. Texto é salvo automaticamente em .txt.
8. Usuário pode copiar ou abrir no Bloco de Notas.
```

Sem login.
Sem internet.
Sem configuração inicial complexa.

---

# Interface sugerida

Tela simples:

```txt
┌────────────────────────────────────────────┐
│  Transcritor PT-BR                         │
│  Status: Ouvindo...                        │
├────────────────────────────────────────────┤
│                                            │
│  [texto transcrito aparece aqui]           │
│                                            │
├────────────────────────────────────────────┤
│ [Pausar] [Copiar] [Abrir no Bloco de Notas]│
└────────────────────────────────────────────┘
```

## Recursos mínimos

| Recurso                          |   Prioridade |
| -------------------------------- | -----------: |
| Começar a ouvir automaticamente  |         Alta |
| Transcrever PT-BR offline        |         Alta |
| Salvar `.txt` automaticamente    |         Alta |
| Botão copiar                     |         Alta |
| Botão abrir no Bloco de Notas    |         Alta |
| Histórico de transcrições        |        Média |
| Atalho global para iniciar/parar |        Média |
| Minimizar para bandeja           |        Média |
| Correção gramatical local        | Baixa no MVP |

---

# Regras de desempenho

Para não pesar no Windows:

```txt
- Usar VAD para ignorar silêncio.
- Usar modelo small int8 como padrão.
- Limitar threads de CPU.
- Processar áudio em blocos.
- Não transcrever a cada 0,5s sem necessidade.
- Evitar Electron.
- Não usar modelo large no MVP.
- Salvar texto incrementalmente, sem manter tudo pesado em RAM.
```

O `whisper.cpp` também tem exemplo de entrada em tempo real, mas a própria documentação descreve o exemplo como ingênuo, com amostragem contínua e transcrição repetida. Para produto final, é melhor controlar blocos de fala e VAD com cuidado. ([GitHub][6])

---

# Comando inicial com UV

```bash
uv init transcritor-ptbr
cd transcritor-ptbr

uv add faster-whisper sounddevice numpy PySide6 pyperclip webrtcvad-wheels
uv add --dev pyinstaller ruff pytest
```

---

# `pyproject.toml` recomendado

```toml
[project]
name = "transcritor-ptbr"
version = "0.1.0"
description = "Aplicativo Windows offline para transcrição PT-BR"
requires-python = ">=3.11"

dependencies = [
    "faster-whisper",
    "numpy",
    "PySide6",
    "pyperclip",
    "sounddevice",
    "webrtcvad-wheels",
]

[dependency-groups]
dev = [
    "pyinstaller",
    "ruff",
    "pytest",
]

[tool.ruff]
line-length = 100
target-version = "py311"
```

---

# MVP em fases

## Fase 1 — Motor funcional

Peso de acerto: **95%**

Objetivo:

```txt
Capturar áudio do microfone
Detectar fala
Transcrever PT-BR offline
Salvar em .txt
```

Sem interface complexa.

## Fase 2 — Interface leve

Peso de acerto: **90%**

Objetivo:

```txt
Criar janela PySide6
Mostrar status: Ouvindo / Transcrevendo / Pausado
Mostrar texto em tempo real
Botão copiar
Botão abrir no Bloco de Notas
```

## Fase 3 — Otimização

Peso de acerto: **85%**

Objetivo:

```txt
Reduzir uso de CPU
Configurar número de threads
Ajustar tamanho dos blocos
Testar modelos base/small/medium
```

## Fase 4 — Empacotamento Windows

Peso de acerto: **80%**

Objetivo:

```txt
Gerar .exe
Incluir modelo local
Criar pasta de logs
Criar pasta de transcrições
Criar instalador simples
```

---

# Configuração padrão do produto

```txt
Nome provisório: Transcritor PT-BR
Sistema: Windows 10/11
Internet: não usa
Idioma: pt-br fixo
Modelo padrão: Whisper small int8
Interface: PySide6
Arquivo de saída: .txt
Logs: UTF-8
Gerenciador: UV
Empacotador: PyInstaller
```

---

# Risco principal

O ponto crítico não é criar a interface.
O ponto crítico é o equilíbrio entre:

```txt
precisão
velocidade
uso de CPU
latência
tamanho do app
```

Para PT-BR, eu não usaria Vosk como motor principal. Apesar de ser offline e leve, a página oficial lista o modelo pequeno de português com WER consideravelmente alto em alguns testes. ([Alpha Cephei][7])

---

# Minha recomendação final

Construir assim:

```txt
MVP:
Python + UV + PySide6 + faster-whisper + modelo small int8

Depois:
Adicionar opção de modelo base/small/medium
Adicionar minimização para bandeja
Adicionar atalho global
Avaliar troca parcial para whisper.cpp se o consumo ficar alto
```

Peso geral de acerto dessa estratégia: **90%**.

A primeira entrega útil deve ser um app que:

```txt
- abre;
- começa a ouvir;
- detecta fala;
- transcreve em PT-BR;
- exibe o texto;
- salva automaticamente em .txt;
- permite copiar;
- permite abrir no Bloco de Notas.
```

[1]: https://github.com/SYSTRAN/faster-whisper?utm_source=chatgpt.com "Faster Whisper transcription with CTranslate2"
[2]: https://github.com/opennmt/ctranslate2?utm_source=chatgpt.com "CTranslate2 - Fast inference engine for Transformer models"
[3]: https://pypi.org/project/PySide6/?utm_source=chatgpt.com "PySide6"
[4]: https://www.pyinstaller.org/?utm_source=chatgpt.com "PyInstaller Manual — PyInstaller 6.20.0 documentation"
[5]: https://openai.com/pt-BR/index/whisper/?utm_source=chatgpt.com "Apresentamos o Whisper"
[6]: https://github.com/ggml-org/whisper.cpp?utm_source=chatgpt.com "ggml-org/whisper.cpp"
[7]: https://alphacephei.com/vosk/models?utm_source=chatgpt.com "VOSK Models"
