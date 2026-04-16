#include <stdio.h>
#define ST 4
#define AL 2
typedef struct { int tr[ST][AL]; int acc[ST]; int start; } DFA;
void dfa_init(DFA *d, int s) {
    d->start=s;
    for(int i=0;i<ST;i++){d->acc[i]=0;for(int j=0;j<AL;j++)d->tr[i][j]=-1;}
}
void dfa_set(DFA *d, int from, int sym, int to) {
    if(from<0||from>=ST||sym<0||sym>=AL) return;
    d->tr[from][sym]=to;
}
int dfa_run(DFA *d, const int *inp, int n) {
    int st=d->start;
    for(int i=0;i<n;i++){ if(st<0)return 0; st=d->tr[st][inp[i]]; }
    return st>=0&&d->acc[st];
}
int dfa_accepts(DFA *d, const int *inp, int n) { return dfa_run(d,inp,n); }
int main(void) {
    DFA d; dfa_init(&d,0);
    dfa_set(&d,0,0,1); dfa_set(&d,1,1,2); d.acc[2]=1;
    int inp[]={0,1};
    printf("accepted=%d\n", dfa_accepts(&d,inp,2));
    return 0;
}
