// Mascot renderer: animates the pixel-art loxodon (data in mascot_data.*).
#pragma once

#include <M5Unified.h>
#include "mascot_data.h"

/**
 * @brief Prepares the mascot sprite and binds it to a draw target.
 *
 * Allocates a 4 bpp palette canvas of MASCOT_W x MASCOT_H (720 bytes of heap)
 * and starts the idle animation. Nothing is drawn until mascot_update().
 *
 * @param dst  Draw target (usually &M5.Display).
 * @param cx   X on @p dst where the figure's vertical axis is placed, in pixels.
 * @param cy   Y of the sprite center on @p dst, in pixels.
 * @param zoom Integer scale factor (4 -> 144x160 on screen).
 * @return true on success; false if the sprite could not be allocated.
 */
bool mascot_begin(LovyanGFX* dst, int32_t cx, int32_t cy, uint8_t zoom);

/**
 * @brief Switches the running animation, restarting it from the first step.
 *
 * Also applies the state's gem colors to the palette. Calling it with the
 * animation already running is a no-op (no restart).
 *
 * @param anim Animation to play (one per assistant state).
 * @return void.
 */
void mascot_set_anim(mascot_anim_id anim);

/**
 * @brief Advances the animation and redraws only when the frame changes.
 *
 * Non-blocking; call it on every loop() iteration.
 *
 * @param now_ms Current time in ms (millis()).
 * @return void.
 */
void mascot_update(uint32_t now_ms);
