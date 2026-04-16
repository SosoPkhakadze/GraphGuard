#ifndef LIST_H
#define LIST_H

typedef struct Node {
    int value;
    struct Node *next;
} Node;

typedef struct {
    Node *head;
    int size;
} List;

void list_push(List *l, int val);
int  list_pop(List *l);
int  list_size(const List *l);

#endif
