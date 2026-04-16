#include <stdio.h>
unsigned char crc8(unsigned char *data, int len) {
    unsigned char crc = 0xFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++)
            crc = (crc & 0x80) ? (unsigned char)((crc<<1)^0x07) : (unsigned char)(crc<<1);
    }
    return crc;
}
int verify(unsigned char *data, int len, unsigned char expected) {
    return crc8(data, len) == expected;
}
int main(void) {
    unsigned char d[]={0x01,0x02,0x03};
    unsigned char c = crc8(d,3);
    printf("crc=%02x valid=%d\n", c, verify(d,3,c));
    return 0;
}
