#include <stdio.h>
#define MWMAX 8
typedef int (*MFn)(int,int*);
typedef struct { MFn chain[MWMAX]; int n; } MWC;
void mw_init(MWC *c) { c->n=0; }
int mw_use(MWC *c, MFn fn) { if(c->n>=MWMAX)return -1; c->chain[c->n++]=fn; return 0; }
int mw_run(MWC *c, int req, int *resp) {
    *resp=req;
    for(int i=0;i<c->n;i++){
        int r=c->chain[i](*resp,resp);
        if(r!=0) return r;
    }
    return 0;
}
int mw_count(MWC *c) { return c->n; }
static int dbl(int r,int *o){*o=r*2;return 0;}
static int inc(int r,int *o){*o=r+1;return 0;}
int main(void) {
    MWC c; mw_init(&c); mw_use(&c,dbl); mw_use(&c,inc);
    int resp; mw_run(&c,5,&resp);
    printf("result=%d count=%d\n", resp, mw_count(&c));
    return 0;
}
