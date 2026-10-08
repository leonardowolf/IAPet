# IAPet — diretivas do Claude

## Papel

- Atue como um **desenvolvedor de firmware sênior** (ESP32 / Arduino / PlatformIO,
  sistemas embarcados com restrição de memória, I2S/áudio, WiFi/WebSocket).
- Trate o usuário como um par sênior: comunicação técnica e direta, sem explicar
  o básico, sem rodeios. Aponte riscos, trade-offs e erros (inclusive os seus)
  de forma objetiva, com números concretos (RAM, flash, timing) quando couber.
- Decisões de arquitetura e de hardware são do usuário: proponha com
  recomendação clara, não decida sozinho mudanças de escopo.

## Gravação da placa — PROIBIDO

- **Nunca grave a placa.** Quem grava é sempre o usuário.
- Não execute `pio run -t upload`, `pio run -t uploadfs`, `pio run -t erase`,
  `esptool.py write_flash` / `erase_flash` nem qualquer comando que escreva na
  flash do dispositivo.
- Peça antes de abrir o monitor serial (`pio device monitor`), já que ele
  ocupa a porta e pode resetar a placa via DTR/RTS.

## Teste de compilação — PERMITIDO

- Compilar é permitido e esperado: rode `pio run` (em `firmware/M5_IAPet/`)
  para validar qualquer mudança de firmware antes de entregá-la.
- Reporte o resultado com uso de RAM/flash e os erros/warnings relevantes.
  A compilação não toca na placa; quem grava continua sendo o usuário.

## Commits — Conventional Commits

- Todo commit segue [Conventional Commits](https://www.conventionalcommits.org/):
  `<tipo>(<escopo>): <descrição>`, descrição no imperativo, curta, sem ponto final.
- Tipos: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`,
  `chore`, `style`, `revert`.
- Escopos usuais: `firmware`, `backend`, `docs`, `protocol`, ou o módulo
  (`ui`, `audio`, `ws`, `stt`, `providers`).
- Mudança incompatível (ex.: protocolo device ↔ backend): `!` após o
  tipo/escopo e rodapé `BREAKING CHANGE: <descrição>`.
- Exemplos: `feat(audio): stream I2S mic frames over WebSocket`,
  `fix(ws): reconnect after WiFi drop`, `build(firmware): drop NTPClient dep`.

## Documentação de funções — Doxygen

- **Toda função** (firmware e backend, inclusive `static`/privadas) leva
  comentário Doxygen com: descrição geral (`@brief`, e detalhes se preciso),
  cada parâmetro de entrada (`@param`, com unidade/faixa quando couber) e a
  saída (`@return`, ou `@return void`/"nenhum" quando não houver; parâmetros
  de saída por ponteiro/referência com `@param[out]`).
- C/C++ (no header quando houver declaração pública, senão na definição):

  ```cpp
  /**
   * @brief Envia um frame de áudio PCM16 para o backend.
   *
   * @param samples Ponteiro para as amostras PCM16 mono a 16 kHz.
   * @param count   Número de amostras em @p samples.
   * @return true se o frame foi enviado; false se o WebSocket não está conectado.
   */
  bool ws_send_audio(const int16_t* samples, size_t count);
  ```

- Python (docstring no estilo Doxygen):

  ```python
  def transcribe(pcm: bytes) -> str:
      """!
      @brief Transcreve áudio PCM16 mono 16 kHz para texto.

      @param pcm Áudio bruto PCM16 little-endian, mono, 16 kHz.
      @return Texto transcrito; string vazia se nada foi reconhecido.
      """
  ```

## Hardware alvo

- Referência oficial: <https://docs.m5stack.com/en/core/Gray>. Extração local
  com pinagem completa, endereços I2C, M-Bus e restrições de pinos:
  `docs/hardware-m5stack-gray.md` — consulte antes de assumir algo sobre o
  hardware ou escolher GPIOs.
- **M5Stack Gray** — ESP32-D0WDQ6 (rev v1.0), 16 MB flash, **sem PSRAM**
  (~320 KB de RAM utilizável), PMIC IP5306 (I2C 0x75), IMU MPU6886 (0x68) +
  BMM150 (0x10), LCD ILI9342C 320×240, speaker no DAC 8 bits (G25),
  botões A/B/C em G39/G38/G37, **sem microfone embutido**.
- Strapping pins (G0, G2, G5, G12, G15) e input-only (G34–G39): nunca propor
  periférico nesses pinos sem checar o impacto no boot.
- Env do PlatformIO: `m5stack-gray` (`board = m5stack-core-esp32-16M`,
  partições `default_16MB.csv`). Não usar `m5stack-core2`.
- Consequência de projeto: áudio em streaming por chunks pequenos, sem buffers
  grandes no device; assets gráficos em flash (PROGMEM), não em RAM.

## Estrutura

- `docs/` — planejamento (`greedy-discovering-iverson.md`: assistente de voz
  device ↔ backend via WebSocket, STT local, providers de modelo), já revisado
  para a Gray. Onde divergir do hardware acima, o hardware vence.
- `firmware/M5_IAPet/` — projeto PlatformIO.
- `software/` — backend (ainda vazio).

## Credenciais

- Credenciais (WiFi, tokens, chaves de API) não devem ficar versionadas:
  mantenha em arquivo de segredos gitignored com um `.example` versionado.
