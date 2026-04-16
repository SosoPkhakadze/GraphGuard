#include "queue.h"

void queue_init(Queue *q) {
    q->count = 0;
}

int queue_push(Queue *q, Task t) {
    if (q->count >= QUEUE_MAX) return -1;
    q->items[q->count++] = t;
    int i = q->count - 1;
    while (i > 0 && q->items[i].priority > q->items[i-1].priority) {
        Task tmp = q->items[i];
        q->items[i] = q->items[i-1];
        q->items[i-1] = tmp;
        i--;
    }
    return 0;
}

int queue_pop(Queue *q, Task *out) {
    if (q->count == 0) return -1;
    *out = q->items[--q->count];
    return 0;
}

int queue_size(const Queue *q) {
    return q->count;
}
