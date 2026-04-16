#ifndef BUF_H
#define BUF_H

#define BUF_SIZE 16

typedef struct {
    int data[BUF_SIZE];
    int head;
    int tail;
    int count;
} RingBuf;

void buf_init(RingBuf *b);
int  buf_write(RingBuf *b, int val);
int  buf_read(RingBuf *b, int *out);
int  buf_size(RingBuf *b);
int  buf_sum(RingBuf *b);
int  buf_full(RingBuf *b);

#endif
