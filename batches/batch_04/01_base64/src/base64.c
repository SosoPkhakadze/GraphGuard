#include <stdio.h>
static const char B64[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
int b64_encode(const unsigned char *in, int n, char *out, int sz) {
    int i=0,j=0;
    while(i<n){
        unsigned a=in[i++];
        unsigned b=i<n?in[i++]:0;
        unsigned c=i<n?in[i++]:0;
        int rem=n-(i-3);
        out[j++]=B64[(a>>2)&0x3F];
        out[j++]=B64[((a&3)<<4)|(b>>4)];
        out[j++]=rem>=2 ? B64[((b&0xF)<<2)|(c>>6)] : '=';
        out[j++]=rem>=3 ? B64[c&0x3F] : '=';
        if(j+4>sz) return -1;
    }
    out[j]='\0'; return j;
}
int b64_len(int n) { return ((n+2)/3)*4; }
int main(void) {
    unsigned char in[]="Man";
    char out[16];
    printf("n=%d s=%s\n", b64_encode(in,3,out,sizeof(out)), out);
    return 0;
}
