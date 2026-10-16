#ifndef LITE_PROTOCOL_CORE_H
#define LITE_PROTOCOL_CORE_H
#include <stdint.h>
#include <string.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define LITE_EQUALS(s,literal) (!strcmp_P(s,PSTR(literal)))
#else
#define LITE_EQUALS(s,literal) (!strcmp(s,literal))
#endif
#include <stdbool.h>
#define LITE_MAX_BYTES 65536UL
/* Strict unsigned decimal; do not accept signs, spaces or wraparound. */
static inline bool lite_parse_size(const char *s, uint32_t *result) {
    uint32_t n = 0;
    if (!*s) return false;
    while (*s) {
        if (*s < '0' || *s > '9') return false;
        uint8_t d = (uint8_t)(*s++ - '0');
        if (n > (LITE_MAX_BYTES - d) / 10UL) return false;
        n = n * 10UL + d;
    }
    if (!n || n > LITE_MAX_BYTES) return false;
    *result = n;
    return true;
}
static inline uint16_t lite_crc_byte(uint16_t crc, uint8_t value) {
    crc ^= (uint16_t)value << 8;
    for (uint8_t i=0; i<8; ++i)
        crc = (crc & 0x8000U) ? (uint16_t)((crc << 1) ^ 0x1021U) : (uint16_t)(crc << 1);
    return crc;
}
/* Supported socket wiring profiles. PINS never changes GPIO direction or rails. */
static inline bool lite_pin_mask(const char *name, uint16_t *mask) {
    if (LITE_EQUALS(name,"27C512")) *mask=0;
    else if (LITE_EQUALS(name,"27C256")) *mask=0x8000U; /* VPP pin 1 HIGH. */
    else if (LITE_EQUALS(name,"27C128")) *mask=0xc000U; /* VPP1 and PGM27 HIGH. */
    else return false;
    return true;
}
static inline bool lite_read_fits(uint32_t size, uint16_t mask) {
    return size && size<=LITE_MAX_BYTES && ((size-1UL)&mask)==0;
}
#endif
