# Assistente remoto M5Stack Gray + Claude (Fase 1: Q&A por voz)

> Revisado em 2026-10-08: plano original foi escrito para o Core2; hardware
> real é a **M5Stack Gray**. Referência de hardware:
> `docs/hardware-m5stack-gray.md`.

## Contexto

O usuário quer um assistente remoto baseado no M5Stack Gray (ESP32) que capture
perguntas por voz, envie para um backend rodando numa máquina (PC/host sempre
ligado), e mostre a resposta em texto na tela. O design deve ser genérico desde
já: o backend expõe uma interface de "provider" de modelo, para que trocar entre
"apenas responde perguntas" (Claude API) e "executa comandos de verdade" (Claude
Code, fase futura) seja só uma troca de configuração, não um redesenho.

Decisões já fechadas com o usuário:
- Fase 1 = somente Q&A (sem execução de comandos ainda).
- Entrada de voz via microfone + STT **já na fase 1** (não vai ter teclado).
- STT local via `faster-whisper` rodando na máquina do backend (sem depender de
  nuvem).
- TTS fica para fase 2 (texto apenas por enquanto).
- Tela mostra o caranguejo da Claude como idle screen por padrão.
- Arquitetura deve ser genérica o bastante pra, no futuro, trocar o "provider"
  por um agente que executa comandos (Claude Code) sem mudar o protocolo
  dispositivo↔backend.

## Impacto do hardware (Gray vs. Core2)

| Recurso | Core2 (plano original) | Gray (real) | Consequência |
|---|---|---|---|
| Microfone | embutido (I2S) | **não tem** | mic I2S externo no M-Bus (ver abaixo) |
| PSRAM | 8 MB | **não tem** (~320 KB heap) | áudio só em streaming, sem buffer de gravação no device |
| Botões | touch virtual | 3 físicos (G39/G38/G37) | push-to-talk no BtnA físico |
| Speaker | amp I2S | DAC 8 bits no G25 | TTS da fase 2 com qualidade limitada |
| PMIC | AXP192 | IP5306 (I2C 0x75) | nível de bateria em 4 degraus (25/50/75/100%) |

### Microfone externo (decisão pendente de hardware)

- Mic MEMS I2S digital (ex.: INMP441, ou módulo I2S equivalente da M5Stack)
  ligado nos pinos I2S do M-Bus:
  - BCK/SCK → **G12** (M-Bus 21)
  - WS → **G13** (M-Bus 22)
  - SD (dados) → **G34** (M-Bus 26, input-only — adequado)
  - L/R → GND (canal esquerdo), VDD → 3V3
- G12 é strapping pin (nível alto no reset = flash 1.8 V, não boota). No
  INMP441 o SCK é entrada do mic, então ele não força o pino; só não pode haver
  pull-up externo em G12. Se o módulo escolhido tiver, remapear BCK para G5
  ou G26.
- **Periférico I2S**: o DAC interno (speaker) só funciona no `I2S_NUM_0`, que o
  M5Unified usa para o speaker. O mic vai no **`I2S_NUM_1`**, configurado via
  `M5.Mic.config()` (pinos e porta customizados).
- Grove A **não serve** para mic PDM: na Gray ele é o mesmo barramento I2C
  interno (G21/G22, onde estão IMU e IP5306).

## Localização e layout do projeto

Repo: `~/Documents/projects/IAPet/`

```
IAPet/
├── CLAUDE.md
├── docs/
│   ├── greedy-discovering-iverson.md   # este plano
│   └── hardware-m5stack-gray.md        # referência de hardware
├── firmware/M5_IAPet/                  # projeto PlatformIO
│   ├── platformio.ini                  # env m5stack-gray
│   ├── src/
│   │   ├── main.cpp           # máquina de estados: idle → ouvindo → pensando → resposta
│   │   ├── config.h           # defines do projeto (sem credenciais)
│   │   ├── secrets.h          # SSID/senha, host do backend (gitignored)
│   │   ├── secrets.h.example  # template versionado
│   │   ├── ui.cpp / ui.h      # tela (idle = caranguejo, estados, texto da resposta)
│   │   ├── audio.cpp / .h     # mic I2S externo via M5.Mic, push-to-talk no BtnA
│   │   └── ws_client.cpp / .h # cliente WebSocket (protocolo abaixo)
│   └── include/claude_crab.h  # bitmap RGB565 em PROGMEM, gerado de um PNG
└── software/                           # backend Python
    ├── requirements.txt
    ├── .env.example           # ANTHROPIC_API_KEY, WHISPER_MODEL, PROVIDER, HOST/PORT
    ├── app/
    │   ├── main.py            # FastAPI, endpoint WebSocket /ws
    │   ├── stt.py             # wrapper faster-whisper (carrega modelo 1x, transcribe(bytes)->str)
    │   └── providers/
    │       ├── base.py        # interface Provider.answer(text: str) -> str
    │       └── claude_qa.py   # ClaudeQAProvider: chama Anthropic Messages API
    └── README.md              # como rodar o backend (venv, .env, uvicorn)
```

## Protocolo dispositivo ↔ backend

Transporte: **WebSocket** em texto claro na LAN (`ws://<backend-host>:<port>/ws`),
sem TLS no device — economiza ~40 KB de heap, relevante sem PSRAM. Escolhido em
vez de HTTP simples porque:
- o backend precisa empurrar mudanças de estado pro device em tempo real
  ("ouvindo" / "pensando" / "resposta" / "erro");
- áudio é naturalmente enviado em chunks binários por uma conexão persistente;
- fase 2 (TTS) reaproveita o mesmo socket pra devolver áudio, sem novo design.

Formato de áudio: PCM16 mono **16 kHz** (taxa nativa do Whisper, sem resample),
frames binários de 512 amostras (1 KB, 32 ms). Throughput 32 KB/s.

Fluxo (fase 1):
1. Boot: Gray conecta WiFi, abre WebSocket com o backend, mostra tela idle
   (caranguejo + status WiFi/bateria).
2. Usuário pressiona e segura o **BtnA físico** (G39) → dispositivo manda
   `{"type":"start"}` e começa a transmitir frames de áudio conforme são lidos
   do I2S. Nada é acumulado no device: cada frame lido é enviado.
3. Tela muda para "Ouvindo...".
4. Ao soltar o botão (ou ao atingir limite de ~15 s) → `{"type":"end"}`.
5. Tela muda para "Pensando...".
6. Backend: concatena os chunks recebidos entre `start` e `end`, roda STT local
   (faster-whisper) → texto; passa o texto pro `Provider.answer(texto)`
   configurado (fase 1 = `ClaudeQAProvider`); manda de volta
   `{"type":"answer","text": "..."}`.
7. Dispositivo recebe `answer`, renderiza o texto (quebra de linha automática,
   rolagem com BtnB/BtnC se não couber) até o usuário apertar BtnA de novo ou
   timeout (~20 s), voltando pro idle.
8. Erros (STT vazio, falha de API, timeout, WS caiu) →
   `{"type":"error","message":...}` ou erro local, mostrado na tela por alguns
   segundos antes de voltar ao idle. Reconexão WiFi/WS automática.

Limite de resposta: o backend instrui o modelo a responder curto e trunca o
`text` (ex.: 1500 caracteres) — a tela tem ~26×15 caracteres na fonte padrão
e o JSON é parseado em RAM.

Esse protocolo e a interface `Provider` já comportam a fase 2 (TTS: backend
manda frames binários de áudio além do `answer`, device toca no DAC via
M5Unified em streaming) e a fase 3 (trocar `ClaudeQAProvider` por um provider
que roda Claude Code com execução de comandos) sem quebrar o contrato — isso
fica documentado como roadmap, **não implementado agora**.

## Firmware (PlatformIO)

- Env `m5stack-gray`: `board = m5stack-core-esp32-16M`,
  `board_build.partitions = default_16MB.csv`, framework `arduino`.
- Libs:
  - `m5stack/M5Unified` — display (M5GFX), botões, speaker (DAC), mic
    (configurado para pinos externos) e bateria (IP5306) numa API só.
  - `links2004/WebSockets` — cliente WebSocket sobre o `WiFi.h` do ESP32.
  - `bblanchon/ArduinoJson` — mensagens de controle.
  - Remover do `platformio.ini` as heranças do datalogger que não se aplicam:
    `NTPClient`, `M5Unit-ENV` (e o `lib/IP5306` local se o M5Unified cobrir a
    leitura de bateria).
- `config.h` atual é herdado do `M5_PS_DATALOGGER` (endpoint Zabbix, token,
  root CA, sensores ENV). Limpar e mover credenciais para `secrets.h`
  gitignored + `secrets.h.example`.
- Orçamento de RAM (sem PSRAM):
  - Sem sprite de tela cheia (320×240×2 = 150 KB): desenhar direto no LCD ou
    usar sprites parciais pequenos (área de texto/status).
  - Caranguejo em PROGMEM, desenhado com `pushImage` direto da flash. Tamanho
    alvo ≤ 160×160 (50 KB de flash, 0 de RAM).
  - Buffer de áudio: DMA do I2S + 1 frame de 1 KB; envio síncrono no loop.
  - Monitorar `ESP.getFreeHeap()` / `getMinFreeHeap()` em build `-D DEBUG`.
- Validação de mudanças: `pio run` (compilação). Gravação na placa é sempre
  feita pelo usuário.

## Backend (Python, em `software/`)

- FastAPI + `uvicorn`, endpoint `/ws` que implementa o protocolo acima.
- `stt.py`: carrega `faster-whisper` uma vez no startup (modelo `base`,
  configurável via `.env`), expõe `transcribe(pcm_bytes) -> str` (PCM16 16 kHz
  mono → float32).
- `providers/base.py`: `class Provider(Protocol): def answer(self, text: str) -> str`.
- `providers/claude_qa.py`: usa o SDK `anthropic`, manda a pergunta pro modelo
  configurado (`.env`: `ANTHROPIC_MODEL`), sem ferramentas — só Q&A puro, com
  system prompt pedindo respostas curtas em texto simples (sem markdown).
- Seleção do provider ativo via `.env` (`PROVIDER=claude_qa`), já deixando o
  ponto de extensão pronto pra um `claude_code.py` futuro.
- `.env.example` documenta `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`,
  `WHISPER_MODEL`, `PROVIDER`, `HOST`, `PORT`.

## Itens em aberto

- **Microfone externo**: escolher o módulo I2S e confirmar pinagem (bloqueia
  `audio.cpp` e o teste ponta a ponta; não bloqueia scaffold, UI, WS e backend).
- Imagem do caranguejo (asset) pra converter em bitmap.
- Chave de API da Claude (`ANTHROPIC_API_KEY`) pro `.env` do backend.
- Qual máquina vai rodar o backend (sempre ligada e acessível na rede local) —
  o endereço é só configuração em `secrets.h`.

## Verificação

1. **Backend isolado**: `cd software && python -m venv .venv && pip install -r
   requirements.txt`, configurar `.env`, rodar `uvicorn app.main:app --reload`,
   testar `/ws` com um script Python mandando `start` / um WAV 16 kHz em chunks
   / `end` e conferindo que volta um `answer` coerente.
2. **Firmware isolado**: `pio run` compila (Claude valida aqui). Gravação e
   monitor serial pelo usuário: confirmar boot, WiFi, WS conectado, tela idle
   com caranguejo e heap livre estável.
3. **Mic**: com o módulo ligado, modo de teste que mostra nível de áudio
   (VU) na tela ao segurar BtnA, antes de integrar com o backend.
4. **Ponta a ponta**: backend rodando e Gray na mesma rede, segurar BtnA,
   falar uma pergunta curta, soltar, e confirmar que a resposta aparece na
   tela em poucos segundos.
