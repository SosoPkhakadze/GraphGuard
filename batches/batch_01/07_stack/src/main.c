#include <stdio.h>
#include "stack.h"

int main() {
    Stack s;
    stack_init(&s);
    stack_push(&s, 10);
    stack_push(&s, 20);
    int val;
    if (stack_pop(&s, &val) == 0)
        printf("Popped: %d\n", val);
    if (stack_peek(&s, &val) == 0)
        printf("Top: %d\n", val);
    return 0;
}
