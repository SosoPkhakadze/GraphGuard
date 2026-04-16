#include <stdio.h>
#define MAXSZ 1000
typedef struct { int size; int max; int rotations; } LR;
void lr_init(LR *l, int max) { l->size=0; l->max=max; l->rotations=0; }
int lr_write(LR *l, int bytes) {
    if(bytes<=0) return -1;
    if(l->size+bytes>l->max){ l->rotations++; l->size=0; }
    l->size+=bytes; return 0;
}
int lr_rotations(LR *l) { return l->rotations; }
int lr_remaining(LR *l) { return l->max-l->size; }
int lr_should_rotate(LR *l, int bytes) { return l->size+bytes>l->max; }
int main(void) {
    LR l; lr_init(&l,MAXSZ);
    lr_write(&l,600); lr_write(&l,600);
    printf("rotations=%d remaining=%d\n", lr_rotations(&l), lr_remaining(&l));
    return 0;
}
