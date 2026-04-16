#include <stdio.h>
#define PSMAX 4
#define SHMAX 4
typedef void (*SubFn)(const char*,const char*);
typedef struct { const char *topic; SubFn h[SHMAX]; int n; } PSSlot;
typedef struct { PSSlot s[PSMAX]; int n; } PS;
void ps_init(PS *p) { p->n=0; }
int ps_sub(PS *p, const char *t, SubFn fn) {
    for(int i=0;i<p->n;i++)
        if(p->s[i].topic==t){if(p->s[i].n>=SHMAX)return -1;p->s[i].h[p->s[i].n++]=fn;return 0;}
    if(p->n>=PSMAX) return -1;
    p->s[p->n].topic=t; p->s[p->n].h[0]=fn; p->s[p->n].n=1; p->n++;
    return 0;
}
int ps_pub(PS *p, const char *t, const char *msg) {
    for(int i=0;i<p->n;i++)
        if(p->s[i].topic==t){ for(int j=0;j<p->s[i].n;j++) p->s[i].h[j](t,msg); return p->s[i].n; }
    return 0;
}
int ps_count(PS *p, const char *t) {
    for(int i=0;i<p->n;i++) if(p->s[i].topic==t) return p->s[i].n;
    return 0;
}
static const char *TA="a";
static void on_msg(const char *t,const char *m){printf("[%s] %s\n",t,m);}
int main(void) {
    PS p; ps_init(&p); ps_sub(&p,TA,on_msg);
    printf("delivered=%d subs=%d\n", ps_pub(&p,TA,"hi"), ps_count(&p,TA));
    return 0;
}
