#include <stdio.h>
#define CB_CLOSED 0
#define CB_OPEN   1
#define CB_HALF   2
typedef struct { int state; int fails; int threshold; } CB;
void cb_init(CB *c, int thr) { c->state=CB_CLOSED; c->fails=0; c->threshold=thr; }
int cb_allow(CB *c) { return c->state!=CB_OPEN; }
void cb_success(CB *c) {
    c->fails=0;
    if(c->state==CB_HALF) c->state=CB_CLOSED;
}
void cb_failure(CB *c) {
    c->fails++;
    if(c->fails>=c->threshold) c->state=CB_OPEN;
}
int cb_state(CB *c) { return c->state; }
int main(void) {
    CB c; cb_init(&c,3);
    cb_failure(&c); cb_failure(&c); cb_failure(&c);
    printf("allow=%d state=%d\n", cb_allow(&c), cb_state(&c));
    return 0;
}
