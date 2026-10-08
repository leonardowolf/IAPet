// GERADO por tools/mascot/build_mascot.py — não editar à mão.
#pragma once
#include <Arduino.h>

#define MASCOT_W 36
#define MASCOT_H 40
#define MASCOT_FRAME_BYTES 720
#define MASCOT_AXIS_X 16  ///< coluna do eixo da figura
#define MASCOT_PALETTE_SIZE 16
#define MASCOT_GEM_CORE_INDEX 11  ///< cor por estado
#define MASCOT_GEM_GLOW_INDEX 12  ///< cor por estado

/** @brief Um passo de animação: quadro exibido e duração. */
typedef struct {
  uint8_t frame;  ///< índice em mascot_frames
  uint16_t ms;    ///< duração do quadro em ms
} mascot_step_t;

/** @brief Animação em loop de um estado, com as cores da gema. */
typedef struct {
  const mascot_step_t* steps;  ///< passos
  uint8_t count;               ///< quantidade de passos
  uint16_t gem_core;           ///< RGB565 do núcleo da gema
  uint16_t gem_glow;           ///< RGB565 do halo da gema
} mascot_anim_t;

/** @brief Índices dos quadros em mascot_frames. */
enum mascot_frame_id : uint8_t {
  MASCOT_FRAME_IDLE_C = 0,
  MASCOT_FRAME_IDLE_BLINK = 1,
  MASCOT_FRAME_IDLE_L = 2,
  MASCOT_FRAME_IDLE_R = 3,
  MASCOT_FRAME_IDLE_SWAY = 4,
  MASCOT_FRAME_LISTEN_READ_A = 5,
  MASCOT_FRAME_LISTEN_READ_B = 6,
  MASCOT_FRAME_LISTEN_LOOK_A = 7,
  MASCOT_FRAME_LISTEN_LOOK_B = 8,
  MASCOT_FRAME_THINK_READ = 9,
  MASCOT_FRAME_THINK_FLIP = 10,
  MASCOT_FRAME_THINK_UP = 11,
  MASCOT_FRAME_THINK_CLOSED = 12,
  MASCOT_FRAME_ANSWER_A = 13,
  MASCOT_FRAME_ANSWER_B = 14,
  MASCOT_FRAME_ERROR_A = 15,
  MASCOT_FRAME_ERROR_B = 16,
  MASCOT_FRAME_COUNT = 17
};

/** @brief Animações disponíveis (uma por estado do assistente). */
enum mascot_anim_id : uint8_t {
  MASCOT_ANIM_IDLE = 0,
  MASCOT_ANIM_LISTENING = 1,
  MASCOT_ANIM_THINKING = 2,
  MASCOT_ANIM_ANSWER = 3,
  MASCOT_ANIM_ERROR = 4,
  MASCOT_ANIM_COUNT = 5
};

extern const uint16_t mascot_palette[MASCOT_PALETTE_SIZE];  ///< RGB565
extern const uint8_t mascot_frames[MASCOT_FRAME_COUNT][MASCOT_FRAME_BYTES];  ///< 4 bpp, nibble alto = pixel da esquerda
extern const mascot_anim_t mascot_anims[MASCOT_ANIM_COUNT];
