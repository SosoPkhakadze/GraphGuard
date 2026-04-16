#include <stdio.h>
#define EBMAX 4
#define EHMAX 4
typedef void (*Hfn)(int,void*);
typedef struct { int ev; Hfn h[EHMAX]; int n; } ESlot;
typedef struct { ESlot s[EBMAX]; int n; } EB;
void eb_init(EB *b) { b->n=0; }
int eb_sub(EB *b, int ev, Hfn h) {
    for(int i=0;i<b->n;i++)
        if(b->s[i].ev==ev){if(b->s[i].n>=EHMAX)return -1;b->s[i].h[b->s[i].n++]=h;return 0;}
    if(b->n>=EBMAX) return -1;
    b->s[b->n].ev=ev; b->s[b->n].h[0]=h; b->s[b->n].n=1; b->n++;
    return 0;
}
int eb_emit(EB *b, int ev, void *data) {
    for(int i=0;i<b->n;i++)
        if(b->s[i].ev==ev){ for(int j=0;j<b->s[i].n;j++) b->s[i].h[j](ev,data); return b->s[i].n; }
    return 0;
}
int eb_count(EB *b, int ev) {
    for(int i=0;i<b->n;i++) if(b->s[i].ev==ev) return b->s[i].n;
    return 0;
}
static void on_ev(int e,void*d){(void)d;printf("event=%d\n",e);}
int main(void) {
    EB b; eb_init(&b); eb_sub(&b,1,on_ev);
    printf("cnt=%d emit=%d\n", eb_count(&b,1), eb_emit(&b,1,0));
    return 0;
}
