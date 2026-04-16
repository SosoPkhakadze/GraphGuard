#include <stdio.h>
int find_min(int *a, int n) {
    int m = a[0];
    for (int i = 1; i < n; i++) if (a[i] < m) m = a[i];
    return m;
}
int find_max(int *a, int n) {
    int m = a[0];
    for (int i = 1; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
int range(int *a, int n) { return find_max(a,n) - find_min(a,n); }
int main(void) {
    int a[]={3,1,4,1,5};
    printf("min=%d max=%d range=%d\n", find_min(a,5), find_max(a,5), range(a,5));
    return 0;
}
