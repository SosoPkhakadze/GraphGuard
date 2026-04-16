#include <stdio.h>
static void swap2(int *a,int *b){int t=*a;*a=*b;*b=t;}
static int partition2(int *a,int lo,int hi){
    int piv=a[hi],i=lo;
    for(int j=lo;j<hi;j++) if(a[j]<=piv){swap2(&a[i],&a[j]);i++;}
    swap2(&a[i],&a[hi]); return i;
}
static int qsel(int *a,int lo,int hi,int k){
    if(lo>=hi) return a[lo];
    int p=partition2(a,lo,hi);
    if(p==k) return a[p];
    if(k<p) return qsel(a,lo,p-1,k);
    return qsel(a,p+1,hi,k);
}
int median(int *a, int n) { return qsel(a,0,n-1,n/2); }
int main(void) {
    int a[]={3,1,4,1,5};
    printf("median=%d\n", median(a,5));
    return 0;
}
