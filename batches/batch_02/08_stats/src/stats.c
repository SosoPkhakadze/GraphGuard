#include <stdio.h>
double mean(double *a, int n) {
    double s=0; for(int i=0;i<n;i++) s+=a[i]; return s/n;
}
double variance(double *a, int n) {
    double m=mean(a,n), s=0;
    for(int i=0;i<n;i++){double d=a[i]-m; s+=d*d;}
    return s/n;
}
double stddev(double *a, int n) {
    double v=variance(a,n), r=v;
    for(int i=0;i<20;i++) r=(r+v/r)/2.0;
    return r;
}
int main(void) {
    double a[]={2,4,4,4,5,5,7,9};
    printf("%.3f %.3f\n", variance(a,8), stddev(a,8));
    return 0;
}
