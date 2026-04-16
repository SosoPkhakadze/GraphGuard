#ifndef QUEUE_H
#define QUEUE_H

#include "task.h"

#define QUEUE_MAX 16

typedef struct {
    Task items[QUEUE_MAX];
    int count;
} Queue;

void queue_init(Queue *q);
int  queue_push(Queue *q, Task t);
int  queue_pop(Queue *q, Task *out);
int  queue_size(const Queue *q);

#endif
