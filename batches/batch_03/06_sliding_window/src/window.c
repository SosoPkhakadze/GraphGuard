#include <stdio.h>
int window_min(int *a, int n, int k) {
    int res = a[0];
    for(int i=0; i<=n-k; i++){
        int loc=a[i];
        for(int j=1;j<k;j++) if(a[i+j]<loc) loc=a[i+j];
        if(i==0||loc<res) res=loc;
    }
    return res;
}
int window_max(int *a, int n, int k) {
    int res=a[0];
    for(int i=0;i<=n-k;i++){
        int loc=a[i];
        for(int j=1;j<k;j++) if(a[i+j]>loc) loc=a[i+j];
        if(i==0||loc>res) res=loc;
    }
    return res;
}
int window_range(int *a, int n, int k) { return window_max(a,n,k)-window_min(a,n,k); }
int main(void) {
    int a[]={3,1,4,1,5,9,2,6};
    printf("min=%d max=%d range=%d\n", window_min(a,8,3), window_max(a,8,3), window_range(a,8,3));
    return 0;
}
