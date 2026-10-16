/* Functional host harness, not an AVR timing/electrical simulator.
 * Includes the real firmware command/receive/dump/GPIO status implementation. */
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <deque>
#include <string>
#include <algorithm>
static uint8_t SREG, MCUSR, DDRC, DDRD, DDRB, PORTD, PORTC, SPCR, SPSR,
UBRR0, UCSR0B, UCSR0C, TCCR0A, TCCR0B, OCR0A, TIMSK0;
static uint16_t socket_address;
static uint8_t spi_high, spi_low;
static std::deque<uint8_t> incoming;
static std::string transmitted;
static size_t inject_stop_at;
static unsigned tx_busy_reads;
static void queue(const char *s) { while(*s) incoming.push_back((uint8_t)*s++); }
struct PortB {
    uint8_t value=0;
    operator uint8_t() const { return value; }
    PortB& operator=(uint8_t v) {
        if(!(value&4) && (v&4)) socket_address=(uint16_t)(spi_high<<8)|spi_low;
        value=v; return *this;
    }
    PortB& operator|=(unsigned v) { return *this=(uint8_t)(value|v); }
    PortB& operator&=(unsigned v) { return *this=(uint8_t)(value&v); }
} PORTB;
struct SpiData {
    uint8_t value=0;
    operator uint8_t() const { return value; }
    SpiData& operator=(uint8_t v) { spi_high=spi_low; spi_low=v; value=v; SPSR|=128; return *this; }
} SPDR;
static uint8_t rom_pattern(uint16_t a) { return (uint8_t)((a*73U+(a>>8))&255); }
struct PinC { operator uint8_t() const { return rom_pattern(socket_address)&63; } } PINC;
struct PinD { operator uint8_t() const { return (rom_pattern(socket_address)>>2)&48; } } PIND;
struct UartFlags {
    operator uint8_t() const { uint8_t ready=tx_busy_reads ? (--tx_busy_reads,0) : 32; return (uint8_t)(ready|(incoming.empty()?0:128)); }
    UartFlags& operator=(uint8_t) { return *this; }
} UCSR0A;
struct UartData {
    operator uint8_t() const { uint8_t c=incoming.front(); incoming.pop_front(); return c; }
    UartData& operator=(uint8_t c) {
        transmitted.push_back((char)c); tx_busy_reads=1;
        if(inject_stop_at && transmitted.size()==inject_stop_at) queue("CON:STOP\n");
        return *this;
    }
} UDR0;
#define __attribute__(x)
#define main firmware_entry
#include "../firmware/lite/main.c"
#undef main
#undef __attribute__
static int checks;
#define CHECK(x) do { if(!(x)) { std::fprintf(stderr,"FAIL firmware line %d: %s\n",__LINE__,#x); std::exit(1); } ++checks; } while(0)
static void run(const char *text) {
    transmitted.clear(); queue(text);
    while(!incoming.empty()) { uint8_t r=receive_line(); if(r==1) command(line); else if(r==2) error_flash(PSTR("FRAME")); }
}
int main() {
    init(); CHECK(!connected && (uint8_t(PORTB)&3)==2 && (PORTD&4)==4);
    run("READ:1\n"); CHECK(transmitted=="ERR:NOTCONNECTED\n");
    run("CON:START\r\n"); CHECK(connected && transmitted=="CON:" DUMPER_IDENTITY "\nINFO:LITE2,MAX=65536,CRC16=1,PINS=1\n");
    CHECK((uint8_t(PORTB)&3)==0 && (PORTD&4)==4);
    status(LED_READING); ticks=499; status_service(); CHECK((uint8_t(PORTB)&3)==1);
    ticks=500; status_service(); CHECK((uint8_t(PORTB)&3)==3);
    ticks=1000; status_service(); CHECK((uint8_t(PORTB)&3)==1);
    for(const char *profile : {"27C512","27C256","27C128"}) {
        run((std::string("PINS:")+profile+"\n").c_str()); CHECK(transmitted=="ACK:PINS\n");
        uint32_t size=pin_high_mask==0 ? 65536UL : pin_high_mask==0x8000 ? 32768UL : 16384UL;
        run((std::string("READ:")+std::to_string(size)+"\n").c_str());
        CHECK(transmitted.size()==4+size*2+10 && transmitted.substr(0,4)=="ACK:");
        uint16_t crc=0xffff; const char *digits="0123456789ABCDEF";
        for(uint32_t a=0;a<size;++a) {
            uint8_t expected=rom_pattern((uint16_t)(a|pin_high_mask));
            CHECK(transmitted[4+a*2]==digits[expected>>4] && transmitted[5+a*2]==digits[expected&15]);
            crc=lite_crc_byte(crc,expected);
        }
        char trailer[16]; std::snprintf(trailer,sizeof(trailer),"\nCRC:%04X\n",crc);
        CHECK(transmitted.substr(4+size*2)==trailer);
        CHECK(socket_address==(uint16_t)((size-1)|pin_high_mask));
        CHECK((PORTD&192)==192 && connected && led_mode==LED_CONNECTED);
    }
    run("READ:16385\n"); CHECK(transmitted=="ERR:SIZE\n");
    run("WRITE:1\n"); CHECK(transmitted=="ERR:COMMAND\n" && led_mode!=LED_WRITING);
    inject_stop_at=24; run("READ:16384\n"); inject_stop_at=0;
    CHECK(transmitted.find("ERR:STOPPED\nCON:STOP\n")!=std::string::npos && transmitted.find("CRC:")==std::string::npos);
    CHECK(!connected && led_mode==LED_NOT_CONNECTED && (PORTD&192)==192);
    run("CON:START\n"); CHECK(connected);
    inject_stop_at=8; run("READ:1\n"); inject_stop_at=0;
    CHECK(transmitted.find("CRC:")!=std::string::npos && transmitted.find("CON:STOP\n")!=std::string::npos && !connected);
    run("CON:START\n"); CHECK(connected);
    run("CON:STOP\n"); CHECK(transmitted=="CON:STOP\n" && !connected && (uint8_t(PORTB)&3)==2);
    run("PINS:27C128\n"); CHECK(transmitted=="ERR:NOTCONNECTED\n");
    std::printf("%d real Lite firmware checks passed on host register shim; no hardware timing claims.\n",checks);
}
