# Assistente Meet

Assistente de reuniao local para Windows que:

- captura o que voce fala pelo microfone;
- captura o audio que sai no alto-falante usando loopback;
- transcreve em tempo real com Whisper rodando localmente;
- salva a reuniao em texto para facilitar pauta, resumo e follow-up.

## Objetivo do projeto

Esta primeira versao prioriza:

- leveza no uso de CPU;
- boa precisao para portugues;
- execucao local, sem depender de enviar audio para a nuvem;
- arquitetura simples para evoluir depois.

## Stack escolhida

- `soundcard`: captura de microfone e loopback do sistema no Windows;
- `faster-whisper`: transcricao local mais leve que a implementacao padrao do Whisper;
- `ollama`: pos-processamento local com um LLM para corrigir a transcricao pelo contexto e gerar pauta e resumo;
- `Typer`: CLI simples para operar o assistente.

## Requisito importante de Python

O projeto usa `Python 3.11`, `3.12` ou `3.13`.

Hoje o seu ambiente local esta em `Python 3.14.4`, e a pilha de transcricao ainda costuma ter melhor compatibilidade em `3.12` ou `3.13`. Por isso o projeto fixa `<3.14`.

Se quiser usar `uv`, o caminho mais direto e:

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
```

## Instalacao

```powershell
uv sync
```

## Listar dispositivos

```powershell
uv run meet-assist devices
```

Esse comando mostra:

- microfones disponiveis;
- dispositivos de saida;
- dispositivos de captura por loopback;
- nomes que podem ser usados nos parametros `--mic-name` e `--speaker-name`.

No Windows, o audio do sistema e capturado pelo dispositivo de `loopback`, que costuma ter o mesmo nome do alto-falante correspondente.

## Iniciar uma reuniao

```powershell
uv run meet-assist record --meeting-name daily --language pt --model small
```

Na primeira execucao, o `faster-whisper` baixa o modelo escolhido para cache local. Depois disso, as proximas execucoes reutilizam esse cache.
`HF_TOKEN` nao e obrigatorio. Ele so ajuda a deixar esse primeiro download mais rapido e com limites maiores no Hugging Face.

Por padrao o app:

- usa o microfone padrao;
- usa o alto-falante padrao para loopback;
- salva arquivos em `transcricoes/`.

Ao encerrar a gravacao, o app tenta gerar automaticamente com `gemma4:latest`:

- tema da reuniao para renomear a pasta da sessao;
- transcricao revisada;
- resumo executivo;
- pauta inferida;

deixe um modelo local no `ollama` disponivel, por exemplo:

```powershell
ollama pull gemma4:latest
uv run meet-assist record --meeting-name daily
```

Se quiser desligar esse passo em uma execucao especifica:

```powershell
uv run meet-assist record --meeting-name daily --no-postprocess
```

Por padrao, a sessao tambem tenta gerar uma diarizacao local heuristica ao encerrar, criando rotulos como `usuario_1`, `usuario_2` e assim por diante.

## Painel desktop e atalho

Se quiser iniciar de forma mais pratica no Windows, abra o arquivo:

```text
Iniciar Assistente Meet.cmd
```

Esse launcher abre um painel nativo do Windows e ja inicia a transcricao automaticamente. O painel mostra:

- botao para iniciar e parar a transcricao;
- status visivel;
- uma mini-janela flutuante com ondas sonoras em tempo real conforme o assistente escuta audio;
- icone proprio na barra de tarefas;
- opcao de abrir a pasta de transcricoes.

Se quiser um atalho de um clique, crie um atalho do arquivo `Iniciar Assistente Meet.cmd` na area de trabalho ou fixe esse atalho na barra de tarefas.

## Exemplos uteis

Capturar so a sua voz:

```powershell
uv run meet-assist record --meeting-name 1-1 --no-speaker
```

Capturar so o audio do computador:

```powershell
uv run meet-assist record --meeting-name demo --no-mic
```

Usar um dispositivo especifico:

```powershell
uv run meet-assist record --mic-name "USB Microphone" --speaker-name "Alto-falantes"
```

Trocar para um modelo mais leve:

```powershell
uv run meet-assist record --model base
```

## Modelos recomendados

- `base`: mais leve, menos preciso;
- `small`: melhor equilibrio entre desempenho e qualidade;
- `medium`: mais preciso, mas mais pesado para CPU.

Para um notebook comum, `small` com `compute_type=int8` tende a ser o melhor ponto de equilibrio.

## Arquivos gerados

Cada sessao cria uma pasta como:

```text
transcricoes/2026-05-07_14-30-00_daily/
```

Dentro dela voce encontra:

- `transcript.md`: leitura humana;
- `events.jsonl`: formato estruturado para futuras integracoes.
- `transcript_diarizado.md`: versao com estimativa de falantes `usuario_1`, `usuario_2` e assim por diante;
- `events_diarized.jsonl`: eventos estruturados com `speaker_label`, quando a diarizacao estiver ativa;
- `transcript_revisado.md`: versao revisada pelo `gemma4`, corrigindo erros comuns de ASR com base no contexto da reuniao;
- `meeting_report.md`: pauta e resumo da reuniao, gerados automaticamente no encerramento quando o pos-processamento estiver ativo.

## Como a transcricao funciona

1. O microfone e o audio do sistema sao capturados em paralelo.
2. Cada fonte e segmentada por energia para evitar mandar silencio ao transcritor.
3. Os trechos com fala entram em uma fila unica.
4. O `faster-whisper` transcreve incrementalmente e salva no disco.
5. Ao encerrar, o app pode estimar falantes por similaridade acustica e gerar uma versao diarizada.
6. Se o pos-processamento estiver ativo, o `gemma4` usa preferencialmente a transcricao diarizada para corrigir palavras com base no contexto, nomear a reuniao, inferir pauta e gerar resumo.

## Ajustes de desempenho

Se quiser deixar ainda mais leve:

- use `--model base`;
- mantenha `--language pt` em vez de autodetectar;
- capture apenas a fonte que realmente importa com `--no-mic` ou `--no-speaker`;
- aumente um pouco `--energy-threshold` se o ambiente tiver muito ruido.

## Limites conhecidos desta primeira versão

- depende do loopback do Windows funcionar corretamente no dispositivo de saida selecionado;
- a diarizacao incluida nesta versao e heuristica e baseada em similaridade acustica local, entao pode confundir vozes parecidas ou audio muito comprimido;
- o pos-processamento com LLM melhora nomeacao, resumo e revisao de texto, mas nao substitui um motor dedicado de ASR ou diarizacao;
- para diarizacao mais robusta em reunioes longas ou com muitos participantes, o proximo passo e plugar um motor especializado de speaker embeddings.

## Troubleshooting

Se o app abrir e fechar na hora:

- rode `uv run meet-assist devices`;
- confira se existe uma tabela `Captura do Sistema (Loopback)`;
- escolha explicitamente uma saida com `--speaker-name`.

Se um filme, chamada ou video nao estiver entrando na transcricao:

- confirme se ele esta saindo no mesmo dispositivo marcado como padrao em `Captura do Sistema (Loopback)`;
- tente informar a saida manualmente, por exemplo `--speaker-name "Alto-falantes"`;
- teste com `--no-mic` para isolar apenas o audio do sistema;
- se o som estiver muito baixo, experimente reduzir o limiar com `--energy-threshold 0.008`.
