#include <stdio.h>
#include <string.h>
#define BF_BITS 256
typedef struct { unsigned char bits[BF_BITS/8]; } Bloom;
static unsigned bfh1(const char *s){unsigned h=5381;while(*s)h=h*33^(unsigned char)*s++;return h%BF_BITS;}
static unsigned bfh2(const char *s){unsigned h=0;while(*s)h=h*31+(unsigned char)*s++;return h%BF_BITS;}
void bf_init(Bloom *b) { memset(b->bits,0,sizeof(b->bits)); }
void bf_add(Bloom *b, const char *s) {
    unsigned h1=bfh1(s),h2=bfh2(s);
    b->bits[h1/8]|=1<<(h1%8); b->bits[h2/8]|=1<<(h2%8);
}
int bf_check(Bloom *b, const char *s) {
    unsigned h1=bfh1(s),h2=bfh2(s);
    return (b->bits[h1/8]>>(h1%8)&1) && (b->bits[h2/8]>>(h2%8)&1);
}
int main(void) {
    Bloom b; bf_init(&b); bf_add(&b,"hello");
    printf("hello=%d world=%d\n", bf_check(&b,"hello"), bf_check(&b,"world"));
    return 0;
}
