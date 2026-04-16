#include <stdio.h>
#define SMAX 8
typedef struct { int id; int prio; int ready; } Task;
typedef struct { Task t[SMAX]; int n; } Sched;
void sched_init(Sched *s) { s->n=0; }
int sched_add(Sched *s, int id, int prio) {
    if(s->n>=SMAX) return -1;
    s->t[s->n].id=id; s->t[s->n].prio=prio; s->t[s->n].ready=1; s->n++;
    return 0;
}
int sched_next(Sched *s) {
    int best=-1;
    for(int i=0;i<s->n;i++){
        if(!s->t[i].ready) continue;
        if(best<0 || s->t[i].prio>s->t[best].prio) best=i;
    }
    if(best>=0) s->t[best].ready=0;
    return best>=0 ? s->t[best].id : -1;
}
void sched_done(Sched *s, int id) {
    for(int i=0;i<s->n;i++) if(s->t[i].id==id){s->t[i].ready=1;break;}
}
int main(void) {
    Sched s; sched_init(&s);
    sched_add(&s,1,5); sched_add(&s,2,10); sched_add(&s,3,3);
    printf("next=%d\n", sched_next(&s));
    return 0;
}
