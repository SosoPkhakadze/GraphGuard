#ifndef TASK_H
#define TASK_H

typedef struct {
    int id;
    int priority;
    char name[32];
} Task;

void task_init(Task *t, int id, int priority, const char *name);
void task_set_priority(Task *t, int priority);
int  task_get_priority(const Task *t);

#endif
