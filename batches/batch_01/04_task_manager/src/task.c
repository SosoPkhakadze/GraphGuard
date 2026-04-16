#include "task.h"
#include <string.h>

void task_init(Task *t, int id, int priority, const char *name) {
    t->id = id;
    t->priority = priority;
    strncpy(t->name, name, 31);
    t->name[31] = '\0';
}

void task_set_priority(Task *t, int priority) {
    if (priority < 0) priority = 0;
    if (priority > 10) priority = 10;
    t->priority = priority;
}

int task_get_priority(const Task *t) {
    return t->priority;
}
