#ifndef STACK_H
#define STACK_H

#define STACK_MAX 64

typedef struct {
    int items[STACK_MAX];
    int top;
} Stack;

void stack_init(Stack *s);
int  stack_push(Stack *s, int val);
int  stack_pop(Stack *s, int *out);
int  stack_peek(Stack *s, int *out);
int  stack_empty(Stack *s);

#endif
