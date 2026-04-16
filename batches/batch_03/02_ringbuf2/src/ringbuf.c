#include <stdio.h>
#define CAP 8
typedef struct { int d[CAP]; int r,w,n; } RBuf;
void rb_init(RBuf *b) { b->r=b->w=b->n=0; }
int rb_push(RBuf *b, int v) {
    if(b->n>=CAP) return -1;
    b->d[b->w]=v; b->w=(b->w+1)%CAP; b->n++;
    return 0;
}
int rb_pop(RBuf *b, int *out) {
    if(b->n<=0) return -1;
    *out=b->d[b->r]; b->r=(b->r+1)%CAP; b->n--;
    return 0;
}
int rb_peek(RBuf *b, int *out) {
    if(b->n<=0) return -1;
    *out=b->d[b->r];
    return 0;
}
int rb_size(RBuf *b) { return b->n; }
int main(void) {
    RBuf b; rb_init(&b);
    rb_push(&b,1); rb_push(&b,2);
    int v; rb_peek(&b,&v);
    printf("peek=%d size=%d\n",v,rb_size(&b));
    rb_pop(&b,&v); printf("pop=%d\n",v);
    return 0;
}
