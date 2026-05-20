# Assistente Meet

Transcreva reunioes e arquivos de audio em portugues, localmente no Windows, sem depender de um servico de transcricao na nuvem.

O Assistente Meet foi pensado para quem precisa acompanhar conversas, entrevistas, aulas, atendimentos ou reunioes e quer manter o audio e os textos no proprio computador.

## O que o aplicativo faz

- capta sua voz pelo microfone;
- capta o audio do computador via loopback do Windows;
- transcreve em tempo real com Whisper offline;
- permite importar arquivos de audio e video para transcricao;
- salva os resultados em arquivos Markdown e JSONL;
- gera uma versao diarizada ao final do processamento.

## Principais vantagens

- processamento local, com foco em privacidade;
- suporte a PT-BR;
- transcricao em tempo real pela interface grafica;
- importacao de arquivos como `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.mp4`, `.mkv`, `.mov` e `.avi`;
- verificacao de atualizacoes pelo proprio aplicativo;
- funcionamento em Windows com interface simples.

## Para quem ele serve

O app e util para:

- reunioes online;
- gravacao de entrevistas;
- aulas e treinamentos;
- analise de ligacoes ou demonstracoes;
- transcricao offline de arquivos ja gravados.

## Privacidade e uso offline

O uso normal do aplicativo acontece localmente no seu computador.

- O audio capturado nao e enviado automaticamente para um servico de transcricao externo.
- As transcricoes ficam salvas na maquina do usuario.
- O app pode verificar atualizacoes online quando essa opcao estiver habilitada.
- Em algumas distribuicoes, o primeiro uso pode precisar preparar ou baixar o modelo Whisper se ele ainda nao estiver disponivel localmente.

## Requisitos

- Windows
- microfone funcional para capturar sua voz
- dispositivo de saida configurado no Windows para capturar o audio do sistema
- conexao com a internet apenas se o modelo precisar ser baixado ou para verificar atualizacoes

## Download e instalacao

Para usuarios finais, a forma recomendada de uso e o instalador publicado na pagina de releases do projeto.

1. Baixe o instalador em `Releases`.
2. Execute o arquivo `Assistente-Meet-Setup.exe`.
3. Conclua a instalacao normalmente.
4. Abra o aplicativo pelo menu Iniciar ou pelo atalho criado.

Se voce preferir a versao portatil, tambem pode usar o executavel distribuido sem instalar, quando esse formato estiver disponivel na release.

## Primeira execucao

Na primeira abertura, confira estes pontos:

1. Escolha o nome da reuniao.
2. Confirme o microfone desejado.
3. Confirme a saida de audio que representa o som do computador.
4. Escolha o modelo Whisper.
5. Clique em `Iniciar Reuniao`.

Modelos disponiveis:

- `tiny`: mais rapido, com menor precisao;
- `base`: leve e bom para maquinas mais simples;
- `small`: melhor equilibrio para a maioria dos casos;
- `medium`: mais preciso, mas mais pesado.

## Como usar

### Transcricao ao vivo

1. Abra o Assistente Meet.
2. Defina o nome da reuniao.
3. Escolha microfone, saida de audio e modelo.
4. Clique em `Iniciar Reuniao`.
5. Acompanhe a transcricao em tempo real na janela principal.
6. Use `Pausar` e `Retomar` quando necessario.
7. Clique em `Encerrar Reuniao` para gerar os arquivos finais.

### Transcricao de arquivo

1. Abra o aplicativo.
2. Clique em `Importar Audio`.
3. Selecione um arquivo de audio ou video.
4. Aguarde a transcricao terminar.
5. Abra a pasta gerada pelo proprio app.

## Onde os arquivos ficam salvos

Quando o aplicativo e usado como programa instalado no Windows, os dados do usuario ficam em:

```text
%LOCALAPPDATA%\Assistente Meet\
```

As principais pastas sao:

- `transcricoes\`: transcricoes e arquivos finais;
- `logs\`: logs do aplicativo;
- `models\`: modelos Whisper usados localmente.

Cada sessao cria uma pasta com data, hora e nome da reuniao, por exemplo:

```text
%LOCALAPPDATA%\Assistente Meet\transcricoes\2026-05-19_19-12-24_daily\
```

Arquivos gerados por sessao:

- `transcript.md`: transcricao principal;
- `events.jsonl`: eventos estruturados da sessao;
- `transcript_diarizado.md`: versao diarizada;
- `events_diarized.jsonl`: eventos diarizados.

## Recursos da interface

- visualizacao da transcricao em tempo real;
- indicador de status;
- visualizador flutuante;
- copia rapida do texto para a area de transferencia;
- abertura do transcript no Bloco de Notas;
- abertura da pasta da sessao;
- verificacao de atualizacoes;
- icone na bandeja do sistema.

## Limitacoes atuais

- a captura do audio do sistema depende do loopback do Windows funcionar corretamente;
- a diarizacao e heuristica e pode confundir vozes parecidas;
- a velocidade da transcricao depende do modelo escolhido, da CPU e da qualidade do audio;
- a qualidade final pode cair em ambientes com ruido, eco ou varias pessoas falando ao mesmo tempo;
- a versao atual do projeto ainda esta em evolucao.

## Solucao de problemas

### O app abre e fecha sozinho

- execute novamente pelo instalador mais recente;
- confira se o Windows reconhece os dispositivos de audio;
- se estiver rodando a partir do codigo-fonte, abra pelo terminal para ver o erro.

### O audio do computador nao esta sendo transcrito

- confirme qual saida esta definida como padrao no Windows;
- selecione manualmente a saida correta no aplicativo;
- teste reproduzir audio no dispositivo escolhido;
- se necessario, reinicie o app apos trocar o dispositivo padrao.

### A transcricao esta lenta

- troque o modelo para `base` ou `tiny`;
- feche programas que estejam consumindo muita CPU;
- use um audio mais limpo, com menos ruido;
- capture apenas a fonte necessaria quando estiver usando a versao de linha de comando.

### O texto saiu com falhas

- aproxime o microfone da fonte de voz;
- reduza ruido ambiente;
- evite sobreposicao de falas;
- teste um modelo maior, como `small` ou `medium`.

## Atualizacoes

O aplicativo possui verificacao de atualizacoes na interface e pode avisar quando uma nova versao estiver disponivel.

Se preferir, voce tambem pode baixar manualmente as novas versoes pela pagina de releases do projeto.

## Para quem vai rodar a partir do codigo-fonte

Se voce quer executar, testar ou empacotar o projeto manualmente:

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
uv run python main.py
```

Comandos uteis:

```powershell
uv run meet-assist devices
uv run meet-assist record --meeting-name daily --language pt --model small
```

Para gerar a build Windows:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_windows.py
```

## Estrutura principal do projeto

```text
main.py
ui/
utils/
models/
logs/
transcricoes/
```
