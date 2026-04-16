#include <stdio.h>
int utf8_charlen(unsigned char c) {
    if(c<0x80) return 1;
    if((c&0xE0)==0xC0) return 2;
    if((c&0xF0)==0xE0) return 3;
    if((c&0xF8)==0xF0) return 4;
    return -1;
}
int utf8_strlen(const char *s) {
    int count=0;
    while(*s){
        int len=utf8_charlen((unsigned char)*s);
        if(len<0) return -1;
        s+=len;
        count++;
    }
    return count;
}
int utf8_valid(const char *s) {
    while(*s){ if(utf8_charlen((unsigned char)*s)<0) return 0; s++; }
    return 1;
}
int main(void) {
    printf("len=%d valid=%d\n", utf8_strlen("hello"), utf8_valid("hello"));
    return 0;
}
