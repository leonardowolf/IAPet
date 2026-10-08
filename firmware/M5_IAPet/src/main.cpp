#include <config.h>
#include <M5Unified.h>
#include "mascot.h"

// Mascot demo: BtnA cycles through the assistant states so the animations
// can be reviewed on the device before the rest of the firmware exists.

static const char* const STATE_LABELS[MASCOT_ANIM_COUNT] = {
    "Repouso", "Ouvindo", "Pensando", "Resposta", "Erro",
};

static uint8_t demo_anim = MASCOT_ANIM_IDLE;

/**
 * @brief Draws the current state name centered below the mascot.
 *
 * @param label Text to show.
 * @return void.
 */
static void draw_label(const char* label)
{
    M5.Display.fillRect(0, 196, M5.Display.width(), 32, mascot_palette[0]);
    M5.Display.setTextDatum(middle_center);
    M5.Display.setTextColor(TFT_WHITE, mascot_palette[0]);
    M5.Display.drawString(label, M5.Display.width() / 2, 212, &fonts::FreeSansBold12pt7b);
}

/**
 * @brief Initializes serial, M5Unified, the display and the mascot.
 *
 * @return void.
 */
void setup()
{
    DEBUG_SERIAL.begin(DEBUG_BAUDRATE);
    M5.begin();
    M5.Display.fillScreen(mascot_palette[0]);

    if (!mascot_begin(&M5.Display, M5.Display.width() / 2, 100, 4)) {
        DEBUG_SERIAL.println("mascot: sprite allocation failed");
    }
    draw_label(STATE_LABELS[demo_anim]);
    DEBUG_SERIAL.printf("IAPet %s - free heap %u\n", FIRMWARE, ESP.getFreeHeap());
}

/**
 * @brief Polls buttons, switches the demo state on BtnA and animates.
 *
 * @return void.
 */
void loop()
{
    M5.update();
    if (M5.BtnA.wasPressed()) {
        demo_anim = (demo_anim + 1) % MASCOT_ANIM_COUNT;
        mascot_set_anim(static_cast<mascot_anim_id>(demo_anim));
        draw_label(STATE_LABELS[demo_anim]);
    }
    mascot_update(millis());
    delay(10);
}
