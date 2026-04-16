#include <stdio.h>
#define CPMAX 4
typedef struct { int id; int in_use; unsigned int acquired_at; } Conn;
typedef struct { Conn c[CPMAX]; unsigned int timeout; } Pool;
void cp_init(Pool *p, unsigned int timeout) {
    p->timeout=timeout;
    for(int i=0;i<CPMAX;i++){p->c[i].id=i;p->c[i].in_use=0;}
}
int cp_acquire(Pool *p, unsigned int now) {
    for(int i=0;i<CPMAX;i++){
        if(!p->c[i].in_use){p->c[i].in_use=1; p->c[i].acquired_at=now; return i;}
    }
    return -1;
}
void cp_release(Pool *p, int id) { if(id>=0&&id<CPMAX) p->c[id].in_use=0; }
int cp_expire(Pool *p, unsigned int now) {
    int count=0;
    for(int i=0;i<CPMAX;i++)
        if(p->c[i].in_use&&now-p->c[i].acquired_at>p->timeout){p->c[i].in_use=0;count++;}
    return count;
}
int main(void) {
    Pool p; cp_init(&p,30);
    int c=cp_acquire(&p,0);
    printf("conn=%d expired=%d\n",c,cp_expire(&p,100));
    cp_release(&p,c);
    return 0;
}
