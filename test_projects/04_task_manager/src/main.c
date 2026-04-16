#include "queue.h"
#include "task.h"
#include <stdio.h>

void scheduler_run(Queue *q);
void scheduler_add(Queue *q, int id, int priority, const char *name);

int main(void) {
    Queue q;
    queue_init(&q);
    scheduler_add(&q, 1, 5, "build");
    scheduler_add(&q, 2, 8, "test");
    scheduler_add(&q, 3, 3, "deploy");
    scheduler_run(&q);
    return 0;
}
