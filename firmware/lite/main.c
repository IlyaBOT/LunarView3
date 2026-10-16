/* Dumper LITE only: two 74HC595, read-only 5 V parallel EPROM.
 * Pin mapping audited against the saved Lite PCB. Not Stage 2 firmware.
 */
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <util/delay.h>
#include <string.h>
#include "protocol_core.h"
#include "identity.h"
#include "../status_core.h"

#define CE _BV(PD6)
#define OE _BV(PD7)
#define LATCH _BV(PB2)
#define DATA_C 0x3fU
#define DATA_D (_BV(PD4) | _BV(PD5))
#define RED _BV(PB0)
#define GREEN _BV(PB1)
#define BLUE _BV(PD2)

static volatile uint32_t ticks;
static uint32_t led_started;
static led_mode_t led_mode=LED_NOT_CONNECTED;
static bool connected;
static uint16_t pin_high_mask;
static char line[48];
static uint8_t used;
static bool bad, dump_active, stop_requested;
static uint32_t last_rx;
static void dump_rx_poll(void);

void watchdog_early(void) __attribute__((naked, section(".init3")));
void watchdog_early(void) { MCUSR=0; wdt_disable(); }

ISR(TIMER0_COMPA_vect) { ++ticks; }
static uint32_t millis(void) {
    uint8_t saved=SREG; cli(); uint32_t t=ticks; SREG=saved; return t;
}

static void controls_off(void) { PORTD |= CE | OE; }
/* Only main context touches GPIO; the timer ISR increments ticks alone. */
static void status_service(void) {
    uint8_t color=led_color(led_mode,millis()-led_started);
    uint8_t b=PORTB | RED | GREEN, d=PORTD | BLUE;
    if (color & RGB_RED) b &= ~RED;
    if (color & RGB_GREEN) b &= ~GREEN;
    if (color & RGB_BLUE) d &= ~BLUE;
    PORTB=b; PORTD=d;
}
static void status(led_mode_t mode) { led_mode=mode; led_started=millis(); status_service(); }
static void idle_status(void) { status(connected ? LED_CONNECTED : LED_NOT_CONNECTED); }
static void uart_send(uint8_t c) {
    while (!(UCSR0A & _BV(UDRE0))) { wdt_reset(); status_service(); if(dump_active) dump_rx_poll(); }
    UDR0=c;
}
static void text_flash(const char *s) { char c; while ((c=pgm_read_byte(s++))) uart_send((uint8_t)c); }
#define SAY(s) text_flash(PSTR(s))
static void hex_byte(uint8_t b) {
    static const char digits[] PROGMEM="0123456789ABCDEF";
    uart_send(pgm_read_byte(digits+(b>>4))); uart_send(pgm_read_byte(digits+(b&15)));
}
static void spi_send(uint8_t v) {
    SPDR=v; while (!(SPSR & _BV(SPIF))) {} (void)SPDR;
}
static void address(uint16_t a) {
    PORTB &= ~LATCH;
    spi_send((uint8_t)(a>>8)); /* U3: A8..A15. */
    spi_send((uint8_t)a);      /* U2: A0..A7. */
    PORTB |= LATCH; _delay_us(1); PORTB &= ~LATCH;
}
static uint8_t rom_read(uint16_t a) {
    controls_off(); address(a | pin_high_mask);
    PORTD &= ~(CE | OE);
    _delay_us(10); /* Conservative settling, including RF5 adapter buffer. */
    uint8_t value=(PINC & DATA_C) | ((PIND & DATA_D)<<2);
    controls_off();
    return value;
}
static void error_flash(const char *reason) {
    controls_off(); idle_status(); SAY("ERR:"); text_flash(reason); uart_send('\n');
}
/* One parser is shared by idle commands and the stop recognizer during output.
 * Parsing while UART waits prevents overrun on the nine-character CON:STOP line.
 * A partial stop line survives the transition from dump to idle. */
static uint8_t receive_line(void) {
    uint8_t flags=UCSR0A, c=UDR0; last_rx=millis();
    if (flags & (_BV(FE0)|_BV(DOR0)|_BV(UPE0))) bad=true;
    if (c=='\r') return 0;
    if (c=='\n') {
        uint8_t result=bad ? 2 : (used ? 1 : 0);
        line[used]=0; used=0; bad=false; return result;
    }
    if (c<32 || c>126 || used>=sizeof(line)-1) bad=true;
    else if(!bad) line[used++]=(char)c;
    return 0;
}
static void dump_rx_poll(void) {
    while (UCSR0A & _BV(RXC0)) {
        if(receive_line()==1 && LITE_EQUALS(line,"CON:STOP")) stop_requested=true;
    }
}
static void dump(uint32_t size) {
    uint16_t crc=0xffff;
    dump_active=true; stop_requested=false;
    status(LED_READING); SAY("ACK:");
    /* uint32_t is essential: 65536 must not wrap a 16-bit loop counter. */
    for (uint32_t a=0; a<size; ++a) {
        status_service(); dump_rx_poll();
        if(stop_requested) break;
        uint8_t value=rom_read((uint16_t)a);
        crc=lite_crc_byte(crc,value); hex_byte(value); wdt_reset();
    }
    controls_off();
    if(stop_requested) {
        dump_active=false;
        connected=false; idle_status(); SAY("\nERR:STOPPED\nCON:STOP\n"); return;
    }
    uart_send('\n'); SAY("CRC:");
    hex_byte((uint8_t)(crc>>8)); hex_byte((uint8_t)crc); uart_send('\n');
    dump_active=false;
    if(stop_requested) { connected=false; idle_status(); SAY("CON:STOP\n"); return; }
    idle_status();
}
static void command(char *text) {
    if (LITE_EQUALS(text,"CON:START")) {
        controls_off(); connected=true; pin_high_mask=0; address(0); idle_status();
        SAY("CON:" DUMPER_IDENTITY "\nINFO:LITE2,MAX=65536,CRC16=1,PINS=1\n"); return;
    }
    if (LITE_EQUALS(text,"CON:STOP")) {
        controls_off(); connected=false; idle_status(); SAY("CON:STOP\n"); return;
    }
    if (!strcmp(text,"INFO:")) { SAY("INFO:LITE2,MAX=65536,CRC16=1,PINS=1\n"); return; }
    if (!strcmp(text,"PING:")) { SAY("ACK:PONG\n"); return; }
    if (!connected) { error_flash(PSTR("NOTCONNECTED")); return; }
    if (!strncmp(text,"PINS:",5)) {
        uint16_t mask;
        if (!lite_pin_mask(text+5,&mask)) { error_flash(PSTR("PINS")); return; }
        controls_off(); pin_high_mask=mask; address(mask); SAY("ACK:PINS\n"); return;
    }
    if (!strncmp(text,"READ:",5)) {
        uint32_t size;
        if (!lite_parse_size(text+5,&size) || !lite_read_fits(size,pin_high_mask)) { error_flash(PSTR("SIZE")); return; }
        dump(size); return;
    }
    error_flash(PSTR("COMMAND"));
}
static void init(void) {
    controls_off(); PORTD |= BLUE | DATA_D;
    PORTB=RED | GREEN; PORTC |= DATA_C;
    DDRC &= ~DATA_C; /* ROM_D0..D5 stay inputs, weak pull-ups enabled. */
    DDRD=(DDRD & ~DATA_D) | CE | OE | BLUE;
    DDRB |= RED | GREEN | LATCH | _BV(PB3) | _BV(PB5);
    DDRB &= ~_BV(PB4); /* ISP MISO stays an input. */
    SPCR=_BV(SPE) | _BV(MSTR) | _BV(SPR0); /* Mode 0, MSB first, F_CPU/16 = 1 MHz. */
    SPSR=0; address(0);
    UCSR0A=_BV(U2X0); UBRR0=16; /* 16 MHz / (8*(16+1)) = 117647 baud, +2.12%. */
    UCSR0B=_BV(RXEN0) | _BV(TXEN0); UCSR0C=_BV(UCSZ01) | _BV(UCSZ00);
    TCCR0A=_BV(WGM01); TCCR0B=_BV(CS01) | _BV(CS00); OCR0A=249; TIMSK0=_BV(OCIE0A);
    status(LED_NOT_CONNECTED); sei(); wdt_enable(WDTO_1S);
}
int main(void) {
    init();
    for (;;) {
        wdt_reset(); status_service();
        if (!(UCSR0A & _BV(RXC0))) {
            if ((used || bad) && millis()-last_rx>=1000UL) {
                used=0; bad=false; error_flash(PSTR("TIMEOUT"));
            }
            continue;
        }
        uint8_t result=receive_line();
        if(result==2) error_flash(PSTR("FRAME"));
        else if(result==1) command(line);
    }
}
