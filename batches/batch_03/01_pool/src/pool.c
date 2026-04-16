#include <stdio.h>
#define POOL_SIZE 256
typedef struct { char mem[POOL_SIZE]; int used; } Pool;
void pool_init(Pool *p) { p->used=0; }
void *pool_alloc(Pool *p, int size) {
    int aligned = (size+3)&~3;
    if (p->used+aligned > POOL_SIZE) return 0;
    void *ptr = p->mem + p->used;
    p->used += aligned;
    return ptr;
}
void pool_reset(Pool *p) { p->used=0; }
int pool_used(Pool *p) { return p->used; }
int main(void) {
    Pool p; pool_init(&p);
    int *a = pool_alloc(&p, sizeof(int));
    *a = 42;
    printf("%d used=%d\n", *a, pool_used(&p));
    pool_reset(&p);
    return 0;
}
