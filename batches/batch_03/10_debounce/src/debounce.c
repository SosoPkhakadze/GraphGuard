#include <stdio.h>
typedef struct { int state; unsigned int last_time; unsigned int delay; } Debounce;
void db_init(Debounce *d, unsigned int delay) { d->state=0; d->last_time=0; d->delay=delay; }
int db_update(Debounce *d, int state, unsigned int now) {
    if(state != d->state){
        if(now - d->last_time >= d->delay){
            d->state=state; d->last_time=now; return 1;
        }
    }
    return 0;
}
int db_state(Debounce *d) { return d->state; }
int main(void) {
    Debounce d; db_init(&d, 50);
    printf("%d %d\n", db_update(&d,1,100), db_state(&d));
    return 0;
}
