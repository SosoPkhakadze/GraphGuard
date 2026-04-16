#include "stack.h"

void stack_init(Stack *s) {
    s->top = -1;
}

int stack_push(Stack *s, int val) {
    if (s->top >= STACK_MAX - 1) return -1;
    s->items[++s->top] = val;
    return 0;
}

int stack_pop(Stack *s, int *out) {
    if (s->top < 0) return -1;
    *out = s->items[s->top--];
    return 0;
}

int stack_peek(Stack *s, int *out) {
    if (s->top < 0) return -1;
    *out = s->items[s->top];
    return 0;
}

int stack_empty(Stack *s) {
    return s->top < 0;
}
