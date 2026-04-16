#include <stdio.h>
#include <string.h>
#define HSZ 16
typedef struct { char k[32]; int v; int used; } HME;
typedef struct { HME e[HSZ]; } HMap;
void hm_init(HMap *h) { memset(h,0,sizeof(*h)); }
static int hm_hash(const char *k) {
    unsigned h=0; while(*k) h=h*31+(unsigned char)*k++;
    return h%HSZ;
}
int hm_set(HMap *h, const char *k, int v) {
    int i=hm_hash(k);
    for(int j=0;j<HSZ;j++){
        int idx=(i+j)%HSZ;
        if(!h->e[idx].used||strcmp(h->e[idx].k,k)==0){
            strncpy(h->e[idx].k,k,31); h->e[idx].v=v; h->e[idx].used=1; return 0;
        }
    }
    return -1;
}
int hm_get(HMap *h, const char *k, int *out) {
    int i=hm_hash(k);
    for(int j=0;j<HSZ;j++){
        int idx=(i+j)%HSZ;
        if(!h->e[idx].used) break;
        if(strcmp(h->e[idx].k,k)==0){*out=h->e[idx].v; return 0;}
    }
    return -1;
}
int hm_contains(HMap *h, const char *k) { int v; return hm_get(h,k,&v)==0; }
int main(void) {
    HMap h; hm_init(&h);
    hm_set(&h,"x",42); int v; hm_get(&h,"x",&v);
    printf("x=%d has=%d\n",v,hm_contains(&h,"x"));
    return 0;
}
