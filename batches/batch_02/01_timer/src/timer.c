#include <stdio.h>
typedef unsigned int uint;
typedef struct { uint start; uint end; } Timer;
void timer_start(Timer *t, uint now) { t->start = now; }
uint timer_elapsed(Timer *t, uint now) {
    if (now < t->start) return 0;
    return now - t->start;
}
void timer_stop(Timer *t, uint now) { t->end = now; }
uint timer_duration(Timer *t) { return t->end - t->start; }
int main(void) {
    Timer t;
    timer_start(&t, 100);
    uint e = timer_elapsed(&t, 200);
    timer_stop(&t, 200);
    printf("%u %u\n", e, timer_duration(&t));
    return 0;
}
