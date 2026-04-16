#include <stdio.h>
#define WIN 4
typedef struct { double buf[WIN]; int pos; int count; double sum; } MovAvg;
void ma_init(MovAvg *m) { m->pos=0; m->count=0; m->sum=0; }
void ma_add(MovAvg *m, double v) {
    if (m->count == WIN) m->sum -= m->buf[m->pos];
    m->buf[m->pos] = v;
    m->sum += v;
    m->pos = (m->pos+1)%WIN;
    if (m->count < WIN) m->count++;
}
double ma_get(MovAvg *m) { return m->count>0 ? m->sum/m->count : 0.0; }
int main(void) {
    MovAvg m; ma_init(&m);
    for(int i=1;i<=6;i++){ma_add(&m,i); printf("%.2f\n",ma_get(&m));}
    return 0;
}
