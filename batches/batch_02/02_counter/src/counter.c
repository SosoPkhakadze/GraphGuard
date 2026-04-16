#include <stdio.h>
typedef struct { int val; int min; int max; } Counter;
void counter_init(Counter *c, int mn, int mx) { c->val=0; c->min=mn; c->max=mx; }
void counter_inc(Counter *c) { if (c->val < c->max) c->val++; }
void counter_dec(Counter *c) {
    if (c->val <= c->min) return;
    c->val--;
}
int counter_get(Counter *c) { return c->val; }
void counter_reset(Counter *c) { c->val = 0; }
int main(void) {
    Counter c; counter_init(&c, 0, 5);
    counter_inc(&c); counter_dec(&c);
    printf("%d\n", counter_get(&c));
    return 0;
}
