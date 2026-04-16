#include <stdio.h>
#define PMAX 10
typedef struct { int p[PMAX+1]; int n; } Prefix;
void prefix_build(Prefix *ps, int *arr, int n) {
    ps->n=n; ps->p[0]=0;
    for(int i=0;i<n;i++) ps->p[i+1]=ps->p[i]+arr[i];
}
int prefix_query(Prefix *ps, int l, int r) {
    return ps->p[r+1]-ps->p[l];
}
int prefix_total(Prefix *ps) { return prefix_query(ps,0,ps->n-1); }
int main(void) {
    int a[]={1,2,3,4,5};
    Prefix ps; prefix_build(&ps,a,5);
    printf("sum=%d total=%d\n", prefix_query(&ps,1,3), prefix_total(&ps));
    return 0;
}
