#include "queue.h"
#include "task.h"
#include <stdio.h>

void scheduler_run(Queue *q) {
    Task t;
    while (queue_pop(q, &t) == 0) {
        printf("Running task %d: %s (priority %d)\n",
               t.id, t.name, t.priority);
    }
}

void scheduler_add(Queue *q, int id, int priority, const char *name) {
    Task t;
    task_init(&t, id, priority, name);
    task_set_priority(&t, priority);
    queue_push(q, t);
}
