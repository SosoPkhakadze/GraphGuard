#include "list.h"
#include <stdio.h>

int main(void) {
    List l = {NULL, 0};
    list_push(&l, 10);
    list_push(&l, 20);
    int sz = list_size(&l);
    int v  = list_pop(&l);
    printf("size=%d val=%d\n", sz, v);
    return 0;
}
