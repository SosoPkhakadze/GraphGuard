#include <stdio.h>
double clamp(double v, double lo, double hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
double normalize(double v, double lo, double hi) {
    double c=clamp(v,lo,hi);
    return (hi==lo)?0.0:(c-lo)/(hi-lo);
}
double lerp(double t, double a, double b) {
    return a + clamp(t,0.0,1.0)*(b-a);
}
int main(void) {
    printf("%.2f %.2f %.2f\n", clamp(5.0,0.0,3.0), normalize(5.0,0.0,10.0), lerp(0.5,0.0,10.0));
    return 0;
}
