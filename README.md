# Assistente Meet

Aplicativo local para Windows focado em transcricao de reunioes em portugues, com processamento offline e exibicao em tempo real.

Hoje o projeto faz isto:

- captura a sua voz pelo microfone;
- captura o audio do computador via loopback;
- transcreve localmente com Whisper;
- mostra os trechos no app enquanto a reuniao acontece;
- salva os arquivos da sessao em `transcricoes/`;
- gera uma versao diarizada ao encerrar a gravacao.

## Objetivo

Esta versao prioriza:

- execucao local, sem enviar audio para a nuvem;
- boa precisao para PT-BR;
- resposta rapida durante a reuniao;
- arquitetura simples para evoluir depois.

## Stack

- `soundcard`: captura de microfone e loopback no Windows;
- `faster-whisper`: motor de transcricao offline;
- `webrtcvad-wheels`: deteccao de voz para evitar mandar silencio ao modelo;
- `PySide6`: interface desktop;
- `Typer`: CLI para operacao e testes rapidos.

## Requisitos

- Windows
- Python `3.11`, `3.12` ou `3.13`
- `uv` instalado

O projeto nao fixa mais `<3.14` no `pyproject.toml`, mas a pilha de audio/transcricao costuma ser mais previsivel em `3.12` ou `3.13`.

Se quiser preparar o ambiente do zero com `uv`:

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
```

## Instalacao

```powershell
uv sync
```

## Como executar

### Interface grafica

Pelo launcher do projeto:

```text
Iniciar Assistente Meet.cmd
```

Ou direto pelo terminal:

```powershell
uv run python main.py
```

O painel permite:

- iniciar, pausar, retomar e encerrar a reuniao;
- acompanhar o status da captura;
- ver a transcricao em tempo real;
- abrir a pasta de transcricoes;
- abrir o transcript no Bloco de Notas.

### Linha de comando

Listar dispositivos:

```powershell
uv run meet-assist devices
```

Iniciar uma reuniao:

```powershell
uv run meet-assist record --meeting-name daily --language pt --model small
```

Na primeira execucao, o `faster-whisper` pode baixar o modelo escolhido. Depois disso, ele reutiliza o cache local.

## Comportamento padrao

Por padrao o app:

- usa o microfone padrao do sistema;
- usa o alto-falante padrao para captura por loopback;
- grava os arquivos da sessao em `transcricoes/`;
- mostra novos blocos de texto durante a reuniao;
- gera diarizacao heuristica ao encerrar.

## Exemplos uteis

Capturar so a sua voz:

```powershell
uv run meet-assist record --meeting-name 1-1 --no-speaker
```

Capturar so o audio do computador:

```powershell
uv run meet-assist record --meeting-name demo --no-mic
```

Usar dispositivos especificos:

```powershell
uv run meet-assist record --mic-name "USB Microphone" --speaker-name "Alto-falantes"
```

Trocar para um modelo mais leve:

```powershell
uv run meet-assist record --model base
```

## Modelos recomendados

- `tiny`: muito rapido, mas menos preciso;
- `base`: leve e util para maquinas mais fracas;
- `small`: melhor equilibrio entre qualidade e desempenho;
- `medium`: mais preciso, mas mais pesado em CPU.

Para a maioria dos notebooks, `small` e o melhor ponto de equilibrio.

## Arquivos gerados

Cada sessao cria uma pasta como:

```text
transcricoes/2026-05-19_19-12-24_daily/
```

Dentro dela voce encontra:

- `transcript.md`: transcript principal em Markdown;
- `events.jsonl`: eventos estruturados com tempo, fonte e texto;
- `transcript_diarizado.md`: versao com rotulos heuristico de falantes;
- `events_diarized.jsonl`: eventos diarizados com `speaker_label`.

Hoje o fluxo principal nao depende de Ollama e nao gera automaticamente `transcript_revisado.md` nem `meeting_report.md`.

## Como a transcricao funciona

1. O microfone e o audio do sistema sao capturados em paralelo.
2. O audio passa por VAD para separar fala de silencio.
3. Trechos de fala entram em uma fila unica.
4. O Whisper transcreve os blocos incrementalmente.
5. O app atualiza a interface e grava os trechos em disco.
6. Ao encerrar, o projeto tenta agrupar falas por similaridade acustica para gerar a versao diarizada.

Para melhorar a sensacao de tempo real, falas longas podem ser quebradas em partes mesmo antes de terminar completamente.

## Limitacoes atuais

- a qualidade da captura do sistema depende do loopback do Windows funcionar corretamente;
- a diarizacao e heuristica, entao pode confundir vozes parecidas;
- a transcricao em tempo real ainda depende do equilibrio entre modelo escolhido, CPU disponivel e qualidade do audio;
- o primeiro download de modelo ainda pode exigir internet, mesmo que o uso normal depois seja offline.

## Troubleshooting

Se o app abrir e fechar na hora:

- rode `uv run meet-assist devices`;
- confirme se os dispositivos de audio aparecem na listagem;
- tente iniciar pelo terminal para ver a mensagem de erro.

Se o audio do computador nao estiver entrando:

- confirme qual saida esta definida como padrao no Windows;
- compare esse nome com a saida exibida em `uv run meet-assist devices`;
- tente informar manualmente `--speaker-name "Alto-falantes"`;
- teste com `--no-mic` para isolar apenas o loopback.

Se a transcricao estiver lenta:

- troque para `--model base`;
- capture apenas a fonte necessaria com `--no-mic` ou `--no-speaker`;
- feche apps pesados que disputem CPU;
- teste primeiro com audio limpo e volume mais alto.

## Estrutura principal

```text
main.py
ui/
utils/
models/
logs/
transcricoes/
```

Os componentes mais importantes hoje sao:

- `main.py`: entrada da CLI e da interface;
- `ui/main_window.py`: janela principal do app;
- `utils/audio_capture.py`: captura de audio;
- `utils/vad_detector.py`: segmentacao de fala;
- `utils/transcriber.py`: integracao com o Whisper;
- `utils/meeting_manager.py`: orquestracao da sessao;
- `utils/text_writer.py`: gravacao dos arquivos.
