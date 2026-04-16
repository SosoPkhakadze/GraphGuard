#include "buf.h"

void buf_init(RingBuf *b) {
    b->head  = 0;
    b->tail  = 0;
    b->count = 0;
}

int buf_write(RingBuf *b, int val) {
    if (b->count >= BUF_SIZE) return -1;
    b->data[b->tail] = val;
    b->tail = (b->tail + 1) % BUF_SIZE;
    b->count++;
    return 0;
}

int buf_read(RingBuf *b, int *out) {
    if (b->count <= 0) return -1;
    *out = b->data[b->head];
    b->head = (b->head + 1) % BUF_SIZE;
    b->count--;
    return 0;
}

int buf_size(RingBuf *b) {
    return b->count;
}
