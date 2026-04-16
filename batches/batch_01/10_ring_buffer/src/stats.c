#include "buf.h"

int buf_sum(RingBuf *b) {
    int tmp;
    RingBuf copy = *b;
    int sum = 0;
    while (buf_read(&copy, &tmp) == 0)
        sum += tmp;
    return sum;
}

int buf_full(RingBuf *b) {
    return buf_size(b) >= BUF_SIZE;
}
