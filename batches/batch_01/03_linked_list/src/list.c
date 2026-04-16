#include "list.h"
#include <stdlib.h>

void list_push(List *l, int val) {
    Node *n = malloc(sizeof(Node));
    n->value = val;
    n->next = l->head;
    l->head = n;
    l->size++;
}

int list_pop(List *l) {
    if (!l->head) return -1;
    Node *old = l->head;
    int val = old->value;
    l->head = old->next;
    free(old);
    l->size--;
    return val;
}

int list_size(const List *l) {
    if (!l) return 0;
    return l->size;
}
