/* Bare-metal ATmega328P, TQFP-32. No bootloader/Arduino dependency.
 * National Fast Algorithm only. All other programming commands are refused.
 */
#include "config.h"
#include "profiles.h"
#include "status_core.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <util/delay.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#define VPP _BV(PD2)
#define RELAY _BV(PD3)
#define CE _BV(PD6)
#define OE _BV(PD7)
#define ARM _BV(PB1)
#define LATCH _BV(PB2)
#define PGM _BV(PB0)
#define DATA_C 0x3f
#define DATA_D (_BV(PD4)|_BV(PD5))
static uint8_t status_bits=0x60; /* Common anode: red at reset. */
static led_mode_t status_mode=LED_NOT_CONNECTED;
static uint32_t status_started;
static void status_service(void);
static uint32_t current_address;
static uint16_t logic_mv=5000;
static volatile uint32_t ticks;
static uint32_t last_heartbeat;
static uint8_t reset_reason __attribute__((section(".noinit")));

/* Disable inherited watchdog before C runtime initialization. */
void early_wdt(void) __attribute__((naked,section(".init3")));
void early_wdt(void) { reset_reason=MCUSR; MCUSR=0; wdt_disable(); }

ISR(TIMER0_COMPA_vect) { ++ticks; }
static uint32_t now_ms(void) {
    uint8_t saved=SREG;cli();uint32_t n=ticks;SREG=saved;return n;
}
static void controls_off(void) { PORTD |= CE|OE; PORTB |= PGM; }
static void data_input(void) { DDRC &= ~DATA_C; PORTC &= ~DATA_C; DDRD &= ~DATA_D; PORTD &= ~DATA_D; }
static void data_output(uint8_t byte) {
    PORTC=(PORTC&~DATA_C)|(byte&DATA_C);
    PORTD=(PORTD&~DATA_D)|((byte>>2)&DATA_D);
    DDRC|=DATA_C; DDRD|=DATA_D;
}
static uint8_t data_sample(void) { return (PINC&DATA_C)|((PIND&DATA_D)<<2); }
static void uart_init(void) {
    UCSR0A=_BV(U2X0);UBRR0= ((F_CPU+4UL*UART_BAUD)/(8UL*UART_BAUD))-1;
    UCSR0B=_BV(RXEN0)|_BV(TXEN0);UCSR0C=_BV(UCSZ01)|_BV(UCSZ00);
}
static void putch(uint8_t c) { while(!(UCSR0A&_BV(UDRE0))){status_service();wdt_reset();} UDR0=c; }
static void puts_flash(const char *s) { char c;while((c=pgm_read_byte(s++)))putch(c); }
#define SAY(s) puts_flash(PSTR(s))
static void puttext(const char*s) { while(*s)putch(*s++); }
static void number(uint32_t n) { char b[11];ultoa(n,b,10);puttext(b); }
static void hex16(uint16_t n) { static const char h[]="0123456789ABCDEF";for(int8_t i=12;i>=0;i-=4)putch(h[(n>>i)&15]); }
static uint16_t crc_add(uint16_t crc,uint8_t byte) {
    crc^=(uint16_t)byte<<8;for(uint8_t i=0;i<8;i++)crc=(crc&0x8000)?(crc<<1)^0x1021:crc<<1;return crc;
}
static int16_t receive(void) {
    uint32_t deadline=now_ms();
    while(!(UCSR0A&_BV(RXC0))) { status_service(); if(now_ms()-deadline>=RX_TIMEOUT_MS)return -1;wdt_reset(); }
    uint8_t flags=UCSR0A,value=UDR0;
    if(flags&(_BV(FE0)|_BV(DOR0)|_BV(UPE0)))return -1;
    return value;
}
/* 0x06 is a keepalive only BETWEEN binary frames, never inside a frame. */
static bool link_alive(void) {
    if(UCSR0A&_BV(RXC0)) {
        uint8_t flags=UCSR0A,c=UDR0;
        if(flags&(_BV(FE0)|_BV(DOR0)|_BV(UPE0))||c!=6)return false;
        last_heartbeat=now_ms();
    }
    return now_ms()-last_heartbeat<RX_TIMEOUT_MS;
}
static void spi_byte(uint8_t b) { SPDR=b;while(!(SPSR&_BV(SPIF))){} (void)SPDR; }
static uint8_t status_value(void) { return ((~led_color(status_mode,now_ms()-status_started))&7U)<<4; }
static void latch_address(uint32_t a) {
    PORTB&=~LATCH;
    spi_byte(((a>>16)&15)|status_bits);spi_byte(a>>8);spi_byte(a);
    PORTB|=LATCH;_delay_us(1);PORTB&=~LATCH;
}
static void address(uint32_t a,const profile_t*p) {
    a&=((1UL<<p->address_bits)-1); current_address=a;
    status_bits=status_value(); latch_address(a);
}
static void status_service(void) {
    if ((PORTD & (CE|OE|VPP))!=(CE|OE) || !(PORTB & PGM)) return;
    uint8_t bits=status_value();
    if(bits!=status_bits) { status_bits=bits; latch_address(current_address); }
}
static void state(led_mode_t mode,const profile_t*p) {
    status_mode=mode;status_started=now_ms();address(current_address,p);
}
static uint16_t adc(uint8_t channel) {
    ADMUX=_BV(REFS0)|channel;_delay_us(25);
    ADCSRA|=_BV(ADSC);while(ADCSRA&_BV(ADSC)){} (void)ADC;
    uint32_t sum=0;
    for(uint8_t i=0;i<8;i++){ADCSRA|=_BV(ADSC);while(ADCSRA&_BV(ADSC)){}sum+=ADC;}
    return (sum+4)/8;
}
static bool calibrate_logic(void) {
    uint16_t raw=adc(14);if(raw<150||raw>350)return false;
    logic_mv=(BANDGAP_MV*1023UL+raw/2)/raw;
    return logic_mv>=4750&&logic_mv<=5250;
}
static uint16_t target_mv(void) {return ((uint32_t)adc(7)*logic_mv*2+511)/1023;}
static uint16_t vpp_mv(void) {return ((uint32_t)adc(6)*logic_mv*142+11253)/(1023UL*22);}
static bool in_range(uint16_t v,uint16_t min,uint16_t max) {return v>=min&&v<=max;}

/* No watchdog refresh inside this bounded electrical discharge wait.
 * A stuck-high VPP leaves the relay energized until watchdog/reset isolation.
 */
static bool vpp_off(void) {
    controls_off(); data_input(); PORTD&=~VPP;
    _delay_ms(3);uint32_t start=now_ms();
    do {if(vpp_mv()<400)return true;}while(now_ms()-start<50);
    return false;
}
static void safe(void) {
    controls_off();data_input();PORTD&=~VPP;PORTB&=~ARM;
    /* Drop the internal source first; allow passive VPP discharge before K1 releases. */
    _delay_ms(10);PORTD&=~RELAY;_delay_ms(20);
}
static void error(const char*message) {safe();SAY("ERR ");puttext(message);putch('\n');}
static uint8_t read_byte(uint32_t a,const profile_t*p,bool program_verify) {
    controls_off();data_input();address(a,p);_delay_us(2);
    if(!program_verify)PORTD&=~OE;
    PORTD&=~CE;_delay_us(10);uint8_t b=data_sample();controls_off();return b;
}
static bool read_power(const profile_t*p) {
    safe();if(!calibrate_logic())return false;
    return in_range(target_mv(),p->read_min_mv,p->read_max_mv)&&vpp_mv()<400;
}
static bool enter_program(const profile_t*p) {
    if(!read_power(p))return false;
    /* Probe the external source through both switches while pin22 is on the READ pole. */
    PORTB|=ARM;_delay_ms(20);PORTD|=VPP;_delay_ms(3);
    bool ok=in_range(vpp_mv(),p->vpp_min_mv,p->vpp_max_mv);
    if(!vpp_off()||!ok)return false;
    PORTD|=RELAY;_delay_ms(25);
    return in_range(target_mv(),p->vcc_min_mv,p->vcc_max_mv);
}
static bool program_byte(uint32_t a,uint8_t desired,const profile_t*p) {
    if(p->algorithm!=1||p->pulse_us!=100||p->max_pulses!=25)return false;
    /* Erased FF bytes need no pulse. A prior whole-device blank check is mandatory. */
    if(desired==0xff)return true;
    address(a,p);
    for(uint8_t attempt=0;attempt<p->max_pulses;attempt++) {
        wdt_reset();controls_off();data_input();if(!link_alive())return false;
        if(!in_range(target_mv(),p->vcc_min_mv,p->vcc_max_mv))return false;
        PORTD|=VPP;_delay_us(2);data_output(desired);_delay_ms(3);
        if(!in_range(vpp_mv(),p->vpp_min_mv,p->vpp_max_mv))return false;
        /* Timer1 provides a bounded pulse with interrupts masked. 16MHz/8 -> 2MHz. */
        uint8_t saved=SREG;cli();TCNT1=0;PORTD&=~CE;
        while(TCNT1<200){} PORTD|=CE;SREG=saved;
        _delay_us(2);if(!vpp_off())return false;
        if(read_byte(a,p,true)==desired)return true;
    }
    return false;
}
static bool lookup(const char *name,profile_t *p) {
    for(uint8_t i=0;i<PROFILE_COUNT;i++) {memcpy_P(p,&profiles[i],sizeof(*p));if(!strcmp(name,p->name))return true;}return false;
}
static void voltages(void) {
    safe();calibrate_logic();SAY("VOLTAGES logic_mv=");number(logic_mv);SAY(" target_mv=");number(target_mv());
    SAY(" vpp_sw_mv=");number(vpp_mv());SAY(" vpp_in=unmeasured\n");
}
static bool frame(uint32_t expected,uint32_t remaining,uint8_t*data,uint16_t*length,uint16_t*image_crc) {
    uint8_t head[6];uint16_t crc=0xffff;
    int16_t magic;
    do {magic=receive();if(magic<0)return false;}while(magic==6);
    if(magic!=0xa5||receive()!=0x5a)return false;
    for(uint8_t i=0;i<6;i++){int16_t b=receive();if(b<0)return false;head[i]=b;crc=crc_add(crc,b);}
    uint32_t off=(uint32_t)head[0]|((uint32_t)head[1]<<8)|((uint32_t)head[2]<<16)|((uint32_t)head[3]<<24);
    uint16_t len=head[4]|((uint16_t)head[5]<<8);
    if(off!=expected||!len||len>FRAME_MAX||len>remaining)return false;
    for(uint16_t i=0;i<len;i++){int16_t b=receive();if(b<0)return false;data[i]=b;crc=crc_add(crc,b);}
    int16_t lo=receive(),hi=receive();if(lo<0||hi<0||crc!=((uint16_t)lo|((uint16_t)hi<<8)))return false;
    for(uint16_t i=0;i<len;i++)*image_crc=crc_add(*image_crc,data[i]);
    last_heartbeat=now_ms();
    *length=len;return true;
}
static bool transfer(const profile_t*p,bool writing,uint16_t*image_crc) {
    uint8_t block[FRAME_MAX];uint32_t off=0;*image_crc=0xffff;
    while(off<p->size) {
        uint16_t len;
        /* Waiting for host always occurs with VPP OFF and MCU data INPUT. */
        if(!vpp_off()||!frame(off,p->size-off,block,&len,image_crc))return false;
        for(uint16_t i=0;i<len;i++) {
            wdt_reset();
            if(writing) {if(!program_byte(off+i,block[i],p))return false;}
            else if(read_byte(off+i,p,false)!=block[i])return false;
        }
        off+=len;SAY("ACK ");number(off);putch('\n');
    }
    return true;
}
static void read_command(const profile_t*p) {
    if(!read_power(p)){error("READ_VOLTAGE");return;}
    state(LED_READING,p);SAY("DATA ");number(p->size);putch('\n');uint16_t crc=0xffff;
    for(uint32_t a=0;a<p->size;a++) {wdt_reset();uint8_t b=read_byte(a,p,false);putch(b);crc=crc_add(crc,b);}
    safe();state(LED_CONNECTED,p);putch('\n');SAY("OK ");hex16(crc);putch('\n');
}
static void verify_command(const profile_t*p) {
    if(!read_power(p)){error("READ_VOLTAGE");return;}
    state(LED_READING,p);SAY("READY 128\n");uint16_t crc;
    if(!transfer(p,false,&crc)){error("VERIFY_MISMATCH_OR_FRAME_TIMEOUT");state(LED_CONNECTED,p);return;}
    safe();state(LED_CONNECTED,p);SAY("OK ");hex16(crc);putch('\n');
}
static void write_command(const profile_t*p) {
    if(!p->program_ok||!p->algorithm){error("PROGRAM_PROFILE_DISABLED");return;}
    if(!HARDWARE_COMMISSIONED){error("HARDWARE_NOT_COMMISSIONED");return;}
    if(!read_power(p)){error("READ_VOLTAGE");return;}
    last_heartbeat=now_ms();
    for(uint32_t a=0;a<p->size;a++) {wdt_reset();if(!link_alive()){error("LINK_TIMEOUT");return;}if(read_byte(a,p,false)!=0xff){error("NOT_ERASED");return;}}
    if(!enter_program(p)){error("PROGRAM_VOLTAGE");return;}
    state(LED_WRITING,p);SAY("READY 128\n");uint16_t programmed_crc,verify_crc;
    if(!transfer(p,true,&programmed_crc)){error("PROGRAM_VERIFY_VOLTAGE_OR_FRAME_TIMEOUT");state(LED_CONNECTED,p);return;}
    safe();if(!read_power(p)){error("FINAL_READ_VOLTAGE");return;}
    state(LED_READING,p);SAY("VERIFY_READY 128\n");
    if(!transfer(p,false,&verify_crc)||programmed_crc!=verify_crc){error("FINAL_VERIFY_FAILED");state(LED_CONNECTED,p);return;}
    safe();state(LED_CONNECTED,p);SAY("OK ");hex16(verify_crc);putch('\n');
}

int main(void) {
    /* Set inactive levels before enabling output drivers. */
    PORTD=CE|OE;PORTB=PGM;DDRD=VPP|RELAY|CE|OE;DDRB=PGM|ARM|LATCH|_BV(PB3)|_BV(PB5);
    data_input();SPCR=_BV(SPE)|_BV(MSTR)|_BV(SPR0);SPSR=0;
    ADCSRA=_BV(ADEN)|_BV(ADPS2)|_BV(ADPS1)|_BV(ADPS0);DIDR0=0;
    TCCR0A=_BV(WGM01);TCCR0B=_BV(CS01)|_BV(CS00);OCR0A=249;TIMSK0=_BV(OCIE0A);
    TCCR1A=0;TCCR1B=_BV(CS11);uart_init();sei();wdt_enable(WDTO_1S);
    profile_t p;memcpy_P(&p,&profiles[0],sizeof(p));safe();state(LED_NOT_CONNECTED,&p);
    char line[64];
    for(;;) {
        uint8_t used=0;bool valid=true;
        for(;;){int16_t c=receive();if(c<0){safe();valid=false;break;}if(c=='\r')continue;if(c=='\n')break;
            if(c<32||c>126||used>=sizeof(line)-1){valid=false;/* Drain to a fresh boundary. */}
            else if(valid)line[used++]=c;}
        if(!valid){safe();while(UCSR0A&_BV(RXC0))(void)UDR0;continue;}
        line[used]=0;controls_off();
        if(!strcmp(line,"INFO")){safe();state(LED_CONNECTED,&p);SAY("INFO protocol=1 profile_hash=" PROFILE_HASH " commissioned=");number(HARDWARE_COMMISSIONED);SAY(" reset=");number(reset_reason);SAY(" device=" PROGRAMMER_ID " revision=" WRITER_STRING(PROGRAMMER_REVISION) " firmware=" PROGRAMMER_VERSION);putch('\n');continue;}
        if(!strcmp(line,"LIST")){safe();for(uint8_t i=0;i<PROFILE_COUNT;i++){memcpy_P(&p,&profiles[i],sizeof(p));puttext(p.name);putch(' ');number(p.size);putch(' ');number(p.read_ok);putch(' ');number(p.program_ok);putch('\n');}SAY("END\n");continue;}
        if(!strcmp(line,"VOLTAGES")){voltages();continue;}
        char*device=strchr(line,' ');if(!device){error("DEVICE_REQUIRED");continue;}*device++=0;
        if(!lookup(device,&p)){error("UNKNOWN_DEVICE");continue;}
        if(!p.read_ok){error("READ_PROFILE_UNVERIFIED");continue;}
        if(!strcmp(line,"READ"))read_command(&p);
        else if(!strcmp(line,"VERIFY"))verify_command(&p);
        else if(!strcmp(line,"WRITE"))write_command(&p);
        else error("INVALID_COMMAND");
    }
}
