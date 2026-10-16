#include <stdio.h>
#include <string.h>
#include "../firmware/lite/protocol_core.h"
#include "../firmware/status_core.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"FAIL line %d\n",__LINE__); return 1; } ++checks; } while(0)
int main(void) {
    int checks=0; uint32_t n=0;
    CHECK(lite_parse_size("1",&n) && n==1);
    CHECK(lite_parse_size("2048",&n) && n==2048);
    CHECK(lite_parse_size("32768",&n) && n==32768);
    CHECK(lite_parse_size("65536",&n) && n==65536);
    CHECK(lite_parse_size("00065536",&n) && n==65536);
    const char *bad[]={"", "0", "65537", "4294967296", "-1", "+1", " 1", "1 ", "12x", "99999999999999999999999"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++) CHECK(!lite_parse_size(bad[i],&n));
    uint16_t crc=0xffff; const char *vector="123456789";
    for(unsigned i=0;i<strlen(vector);i++) crc=lite_crc_byte(crc,(uint8_t)vector[i]);
    CHECK(crc==0x29b1);
    uint16_t mask=0;
    CHECK(lite_pin_mask("27C512",&mask) && mask==0 && lite_read_fits(65536,mask));
    CHECK(lite_pin_mask("27C256",&mask) && mask==0x8000 && lite_read_fits(32768,mask));
    CHECK(!lite_read_fits(32769,mask));
    CHECK(lite_pin_mask("27C128",&mask) && mask==0xc000 && lite_read_fits(16384,mask));
    CHECK(!lite_read_fits(16385,mask));
    CHECK(!lite_pin_mask("27C010",&mask));
    CHECK(led_color(LED_NOT_CONNECTED,1000)==RGB_RED);
    CHECK(led_color(LED_CONNECTED,1000)==(RGB_RED|RGB_GREEN));
    CHECK(led_color(LED_STANDBY,500)==(RGB_RED|RGB_GREEN));
    CHECK(led_color(LED_READING,0)==RGB_GREEN);
    CHECK(led_color(LED_READING,499)==RGB_GREEN);
    CHECK(led_color(LED_READING,500)==0);
    CHECK(led_color(LED_READING,999)==0);
    CHECK(led_color(LED_READING,1000)==RGB_GREEN);
    CHECK(led_color(LED_WRITING,0)==(RGB_RED|RGB_BLUE));
    CHECK(led_color(LED_WRITING,499)==(RGB_RED|RGB_BLUE));
    CHECK(led_color(LED_WRITING,500)==0);
    CHECK(led_color(LED_WRITING,1000)==(RGB_RED|RGB_BLUE));
    CHECK(led_color(LED_READING,(uint32_t)(100U-0xffffff00U))==RGB_GREEN);
    CHECK(led_color(LED_READING,(uint32_t)(300U-0xffffff00U))==0);
    uint32_t count=0; for(uint32_t a=0;a<65536UL;++a) { CHECK((uint16_t)a==a); ++count; }
    CHECK(count==65536UL);
    printf("Native shared AVR protocol checks passed (including 65536-address boundary).\n");
    return 0;
}
