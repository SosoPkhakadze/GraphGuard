#include <stdio.h>
#define WORDS 4
typedef struct { unsigned int w[WORDS]; } Bitset;
void bs_set(Bitset *b, int i) { b->w[i/32] |= 1u<<(i%32); }
void bs_clear(Bitset *b, int i) { b->w[i/32] &= ~(1u<<(i%32)); }
int bs_test(Bitset *b, int i) { return (b->w[i/32]>>(i%32))&1; }
int bs_count(Bitset *b) {
    int n = 0;
    for (int i = 0; i < WORDS; i++) {
        unsigned int w = b->w[i];
        while (w) { n += w&1; w>>=1; }
    }
    return n;
}
int main(void) {
    Bitset b = {0};
    bs_set(&b,1); bs_set(&b,5); bs_set(&b,33);
    printf("count=%d\n", bs_count(&b));
    return 0;
}
