#pragma once
#include <stdint.h>
#define _BV(x) (1U<<(x))
enum { PB0=0, PB1=1, PB2=2, PB3=3, PB4=4, PB5=5, PD2=2, PD4=4, PD5=5, PD6=6, PD7=7,
UDRE0=5, RXC0=7, FE0=4, DOR0=3, UPE0=2, U2X0=1, RXEN0=4, TXEN0=3, UCSZ01=2, UCSZ00=1,
SPIF=7, SPE=6, MSTR=4, SPR0=0, WGM01=1, CS01=1, CS00=0, OCIE0A=1 };
