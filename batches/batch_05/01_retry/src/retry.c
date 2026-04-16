#include <stdio.h>
typedef int (*Fn)(void*);
int retry_run(Fn fn, void *ctx, int max, unsigned int delay) {
    for(int i=0;i<max;i++){
        if(fn(ctx)==0) return 0;
        if(i<max-1){ unsigned int w=delay<<i; (void)w; }
    }
    return -1;
}
int retry_count(Fn fn, void *ctx, int max) {
    int n=0;
    for(int i=0;i<max;i++){ n++; if(fn(ctx)==0) break; }
    return n;
}
static int always_fail(void *c){(void)c;return -1;}
static int always_ok(void *c){(void)c;return 0;}
int main(void) {
    printf("fail=%d ok=%d\n", retry_run(always_fail,0,3,10), retry_run(always_ok,0,3,10));
    return 0;
}
