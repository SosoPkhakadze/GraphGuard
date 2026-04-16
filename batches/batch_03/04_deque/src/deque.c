#include <stdio.h>
#define DQCAP 8
typedef struct { int d[DQCAP]; int front,back,n; } Deque;
void dq_init(Deque *q) { q->front=q->back=q->n=0; }
int dq_push_back(Deque *q, int v) {
    if(q->n>=DQCAP) return -1;
    q->d[q->back]=v; q->back=(q->back+1)%DQCAP; q->n++;
    return 0;
}
int dq_pop_front(Deque *q, int *out) {
    if(q->n<=0) return -1;
    *out=q->d[q->front];
    q->front=(q->front+1)%DQCAP;
    q->n--;
    return 0;
}
int dq_front(Deque *q, int *out) {
    if(q->n<=0) return -1;
    *out=q->d[q->front]; return 0;
}
int dq_size(Deque *q) { return q->n; }
int main(void) {
    Deque q; dq_init(&q);
    for(int i=0;i<5;i++) dq_push_back(&q,i*10);
    int v; dq_pop_front(&q,&v);
    printf("popped=%d size=%d\n",v,dq_size(&q));
    return 0;
}
