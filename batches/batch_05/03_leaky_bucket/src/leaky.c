#include <stdio.h>
#define LBCAP 100
typedef struct { int level; int rate; unsigned int last; } LB;
void lb_init(LB *b, int rate) { b->level=0; b->rate=rate; b->last=0; }
static void lb_drain(LB *b, unsigned int now) {
    unsigned int elapsed=now-b->last;
    int drain=(int)elapsed*b->rate;
    b->level-=drain;
    b->last=now;
    if(b->level<0) b->level=0;
}
int lb_add(LB *b, int amount, unsigned int now) {
    lb_drain(b,now);
    if(b->level+amount>LBCAP) return -1;
    b->level+=amount; return 0;
}
int lb_level(LB *b) { return b->level; }
int main(void) {
    LB b; lb_init(&b,10);
    lb_add(&b,50,0); lb_add(&b,30,3);
    printf("level=%d\n", lb_level(&b));
    return 0;
}
