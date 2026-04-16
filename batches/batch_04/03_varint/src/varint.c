#include <stdio.h>
int varint_encode(unsigned int v, unsigned char *out, int sz) {
    int i=0;
    do {
        if(i>=sz) return -1;
        out[i] = v&0x7F;
        if(v>>7) out[i]|=0x80;
        v>>=7; i++;
    } while(v);
    return i;
}
int varint_decode(const unsigned char *in, int sz, unsigned int *out) {
    unsigned int v=0; int sh=0,i=0;
    do { if(i>=sz) return -1; v|=(unsigned int)(in[i]&0x7F)<<sh; sh+=7; i++; } while(in[i-1]&0x80);
    *out=v; return i;
}
int varint_size(unsigned int v) { int n=1; while(v>=128){v>>=7;n++;} return n; }
int main(void) {
    unsigned char buf[8];
    int n=varint_encode(300,buf,sizeof(buf));
    unsigned int v; varint_decode(buf,n,&v);
    printf("bytes=%d val=%u\n",n,v);
    return 0;
}
