#include "mascot.h"

static M5Canvas sprite;
static LovyanGFX* target = nullptr;
static int32_t center_x = 0;
static int32_t center_y = 0;
static float scale = 1.0f;

static mascot_anim_id current_anim = MASCOT_ANIM_IDLE;
static uint8_t current_step = 0;
static uint32_t step_started_ms = 0;
static bool needs_redraw = true;

/**
 * @brief Sets one sprite palette entry from an RGB565 color.
 *
 * @param index Palette index (0-15).
 * @param c     Color in RGB565.
 * @return void.
 */
static void set_palette_565(uint8_t index, uint16_t c)
{
    sprite.setPaletteColor(index, (c >> 8) & 0xF8, (c >> 3) & 0xFC, (c << 3) & 0xF8);
}

/**
 * @brief Loads the gem colors of an animation into the sprite palette.
 *
 * @param anim Animation whose gem colors are applied.
 * @return void.
 */
static void apply_gem_colors(mascot_anim_id anim)
{
    set_palette_565(MASCOT_GEM_CORE_INDEX, mascot_anims[anim].gem_core);
    set_palette_565(MASCOT_GEM_GLOW_INDEX, mascot_anims[anim].gem_glow);
}

/**
 * @brief Copies one 4 bpp frame into the palette sprite and pushes it scaled.
 *
 * @param frame Index into mascot_frames.
 * @return void.
 */
static void draw_frame(uint8_t frame)
{
    const uint8_t* data = mascot_frames[frame];
    for (int y = 0; y < MASCOT_H; y++) {
        for (int x = 0; x < MASCOT_W; x += 2) {
            uint8_t b = data[(y * MASCOT_W + x) / 2];
            sprite.drawPixel(x, y, b >> 4);       // palette sprite: color = index
            sprite.drawPixel(x + 1, y, b & 0x0F);
        }
    }
    sprite.pushRotateZoom(target, center_x, center_y, 0.0f, scale, scale);
}

bool mascot_begin(LovyanGFX* dst, int32_t cx, int32_t cy, uint8_t zoom)
{
    target = dst;
    // pushRotateZoom anchors the sprite center; shift so the figure axis lands on cx.
    center_x = cx + (MASCOT_W / 2 - MASCOT_AXIS_X) * zoom;
    center_y = cy;
    scale = zoom;

    sprite.setColorDepth(4);
    if (!sprite.createSprite(MASCOT_W, MASCOT_H)) {
        return false;
    }
    sprite.createPalette();
    for (int i = 0; i < MASCOT_PALETTE_SIZE; i++) {
        set_palette_565(i, mascot_palette[i]);
    }

    current_anim = MASCOT_ANIM_IDLE;
    apply_gem_colors(current_anim);
    current_step = 0;
    step_started_ms = millis();
    needs_redraw = true;
    return true;
}

void mascot_set_anim(mascot_anim_id anim)
{
    if (anim == current_anim || anim >= MASCOT_ANIM_COUNT) {
        return;
    }
    current_anim = anim;
    apply_gem_colors(anim);
    current_step = 0;
    step_started_ms = millis();
    needs_redraw = true;
}

void mascot_update(uint32_t now_ms)
{
    if (target == nullptr) {
        return;
    }
    const mascot_anim_t& anim = mascot_anims[current_anim];
    if (now_ms - step_started_ms >= anim.steps[current_step].ms) {
        current_step = (current_step + 1) % anim.count;
        step_started_ms = now_ms;
        needs_redraw = true;
    }
    if (needs_redraw) {
        draw_frame(anim.steps[current_step].frame);
        needs_redraw = false;
    }
}
