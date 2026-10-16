#ifndef DUMPER_STATUS_CORE_H
#define DUMPER_STATUS_CORE_H
#include <stdint.h>
/* Logical RGB channels; board-specific active-low GPIO mapping stays in main.c. */
enum { RGB_RED=1, RGB_GREEN=2, RGB_BLUE=4 };
typedef enum { LED_NOT_CONNECTED, LED_STANDBY, LED_CONNECTED, LED_READING, LED_WRITING } led_mode_t;
static inline uint8_t led_color(led_mode_t mode, uint32_t elapsed_ms) {
    if (mode==LED_READING || mode==LED_WRITING) {
        if ((elapsed_ms/500UL)&1U) return 0;
        return mode==LED_READING ? RGB_GREEN : RGB_RED|RGB_BLUE;
    }
    return mode==LED_NOT_CONNECTED ? RGB_RED : RGB_RED|RGB_GREEN;
}
#endif
