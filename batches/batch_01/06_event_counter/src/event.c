#include <stdio.h>

static int event_count = 0;

void event_fire() {
    event_count++;
}

void event_reset() {
    event_count = 0;
}

int event_get_count() {
    return event_count;
}

int main() {
    event_fire();
    event_fire();
    event_reset();
    int c = event_get_count();
    printf("Count: %d\n", c);
    return 0;
}
