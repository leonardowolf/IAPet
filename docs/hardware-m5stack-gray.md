# Referência de hardware — M5Stack Gray (K002)

Fonte: <https://docs.m5stack.com/en/core/Gray> (conferido em 2026-10-08).
Notas marcadas com **[nota]** não estão na página: são observações de
projeto sobre o ESP32 que afetam o uso dos pinos.

## Núcleo

| Item | Valor |
|---|---|
| SoC | ESP32-D0WDQ6, Xtensa LX6 dual-core @ 240 MHz (600 DMIPS) |
| SRAM | 520 KB (interna; ~320 KB livres para heap na prática) |
| PSRAM | **não tem** |
| Flash | 16 MB |
| Wi-Fi | 2.4 GHz (+ BT do ESP32) |
| USB | Type-C (USB-serial para upload/monitor) |
| Operação | 0 ~ 60 °C |
| Dimensões / peso | 54.0 × 54.0 × 17.0 mm / 47.7 g |

PlatformIO: env `m5stack-gray` → `board = m5stack-core-esp32-16M` +
`board_build.partitions = default_16MB.csv` (a página não indica board name).

## Mapa de pinos interno

| Função | GPIO | Observação |
|---|---|---|
| LCD MOSI / MISO / CLK | G23 / G19 / G18 | SPI compartilhado com o TF card |
| LCD CS | G14 | |
| LCD DC | G27 | |
| LCD RST | G33 | |
| LCD backlight | G32 | |
| TF card CS | G4 | mesmo barramento SPI do LCD; até 16 GB |
| Botão A / B / C | G39 / G38 / G37 | input-only, sem pull-up interno **[nota]** |
| Speaker (1 W, 0928) | G25 | DAC1, 8 bits |
| I2C interno SDA / SCL | G21 / G22 | MPU6886, BMM150, IP5306 |

### Dispositivos I2C internos (G21/G22)

| Chip | Endereço | Função |
|---|---|---|
| MPU6886 | 0x68 | acelerômetro + giroscópio 3 eixos |
| BMM150 | 0x10 | magnetômetro 3 eixos (sofre interferência de ímãs, inclusive de módulos M5 empilhados) |
| IP5306 | 0x75 | PMIC/carregador — versão I2C customizada |

### Display

ILI9342C, 320×240, IPS 2", até 853 nit.

### Energia

Bateria 110 mAh @ 3.7 V; entrada 5 V @ 500 mA. Com Wi-Fi ativo a autonomia
da bateria interna é curta — tratar como alimentado por USB **[nota]**.

## Grove A (vermelho, I2C)

| Sinal | GPIO |
|---|---|
| SDA | G21 |
| SCL | G22 |
| 5V / GND | — |

Mesmo barramento do I2C interno. **[nota]** A página tem uma inconsistência
(numa listagem aparece G21=SCL / G22=SDA); a tabela de pinagem, o M-Bus e o
padrão do `Wire` do ESP32 concordam em **G21=SDA, G22=SCL**.

## M-Bus (header 30 pinos)

| Esquerda | Pino | Pino | Direita |
|---|---|---|---|
| GND | 1 | 2 | G35 (ADC) |
| GND | 3 | 4 | G36 (ADC) |
| GND | 5 | 6 | RST (EN) |
| G23 MOSI | 7 | 8 | G25 DAC/SPK |
| G19 MISO | 9 | 10 | G26 DAC |
| G18 SCK | 11 | 12 | 3V3 |
| G3 RXD0 | 13 | 14 | G1 TXD0 |
| G16 RXD2 | 15 | 16 | G17 TXD2 |
| G21 SDA (int) | 17 | 18 | G22 SCL (int) |
| G2 GPIO | 19 | 20 | G5 GPIO |
| G12 I2S_SK | 21 | 22 | G13 I2S_WS |
| G15 I2S_OUT | 23 | 24 | G0 I2S_MK |
| HPWR | 25 | 26 | G34 I2S_IN |
| HPWR | 27 | 28 | 5V |
| HPWR | 29 | 30 | BAT |

## ADC / DAC

- ADC1: 8 canais (G32–G39). ADC2: 10 canais (G0/2/4/12–15/25–27).
- DAC: G25 (speaker), G26 (livre no M-Bus).
- **[nota]** ADC2 não funciona com Wi-Fi ligado → usar só ADC1 neste projeto.

## Restrições de pinos (**[nota]** — ESP32, não constam na página)

- **G34–G39 são input-only** e sem pull-up/pull-down interno.
- **Strapping pins: G0, G2, G5, G12, G15.** G12 (MTDI) em nível alto no boot
  seleciona flash a 1.8 V e impede o boot; G0 em baixo entra em modo download.
  Periféricos ligados a esses pinos não podem forçar nível no reset.
- G1/G3 são a UART0 (USB-serial: upload e log) — não reutilizar.
- G16/G17 livres (UART2), pois a Gray não tem PSRAM ocupando esses pinos.

## Ausências relevantes para o projeto

- **Sem microfone.** Captura de voz exige mic externo. Pinos I2S previstos no
  M-Bus: SCK G12, WS G13, DATA_IN G34 (input-only, adequado para mic).
  Atenção: G12 é strapping — o mic não pode puxar SCK para alto no boot.
- **Sem PSRAM.** Áudio em streaming por chunks pequenos; bitmaps em flash
  (PROGMEM), não em RAM; cuidado com TLS + buffers de WebSocket simultâneos.
- **Speaker no DAC de 8 bits** (G25): qualidade limitada e ruído/"pop" ao
  ligar; manter o DAC mudo quando não estiver tocando **[nota]**.

## Histórico de revisões

| Data | Mudança |
|---|---|
| 2019.6 | MPU9250 → MPU6886 + BMM150 |
| 2019.7 | Tela TN → IPS |
| 2020.3 | Bateria 150 mAh → 110 mAh |
