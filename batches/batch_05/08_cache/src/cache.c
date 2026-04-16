#include <stdio.h>
#include <string.h>
#define CSZ 4
typedef struct { int key; int val; int age; } CE;
typedef struct { CE e[CSZ]; int tick; } Cache;
void cache_init(Cache *c) { c->tick=0; memset(c->e,0,sizeof(c->e)); }
void cache_put(Cache *c, int k, int v) {
    for(int i=0;i<CSZ;i++)
        if(c->e[i].key==k){c->e[i].val=v;c->e[i].age=c->tick++;return;}
    int old=0;
    for(int i=1;i<CSZ;i++) if(c->e[i].age<c->e[old].age) old=i;
    c->e[old]=(CE){k,v,c->tick++};
}
int cache_get(Cache *c, int k, int *out) {
    for(int i=0;i<CSZ;i++)
        if(c->e[i].key==k){c->e[i].age=c->tick++;*out=c->e[i].val;return 1;}
    return 0;
}
int cache_stale(Cache *c, int max_age) {
    int n=0; for(int i=0;i<CSZ;i++) if(c->e[i].age<max_age) n++;
    return n;
}
int main(void) {
    Cache c; cache_init(&c);
    cache_put(&c,1,10); cache_put(&c,2,20);
    int v; cache_get(&c,1,&v);
    printf("v=%d stale=%d\n",v,cache_stale(&c,2));
    return 0;
}
