/* Generated from device_profiles.json by tools/generate_profiles.py. */
#pragma once
#include <stdint.h>
#include <avr/pgmspace.h>
#define PROFILE_HASH "8abe590fa20ac2f1"
#define PROFILE_COUNT 12
typedef struct { char name[16]; uint32_t size; uint8_t address_bits, read_ok, program_ok, algorithm; uint16_t read_min_mv, read_max_mv, vcc_min_mv, vcc_max_mv, vpp_min_mv, vpp_max_mv, pulse_us; uint8_t max_pulses; } profile_t;
static const profile_t profiles[PROFILE_COUNT] PROGMEM = {
  {"NM27C512", 65536, 16, 1, 1, 1, 4750, 5250, 6000, 6500, 12500, 13000, 100, 25},
  {"27C512", 65536, 16, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"INTEL2716", 2048, 11, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"INTEL2732", 4096, 12, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"INTEL2764", 8192, 13, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"INTEL27128A", 16384, 14, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"INTEL27256", 32768, 15, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"KR573RF5", 2048, 11, 0, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"NM27C010", 131072, 17, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"NM27C020", 262144, 18, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"NM27C040", 524288, 19, 1, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
  {"NM27C080", 1048576, 20, 0, 0, 0, 4750, 5250, 0, 0, 0, 0, 0, 0},
};
