#include <stdio.h>
#include "buf.h"

int main() {
    RingBuf b;
    buf_init(&b);
    buf_write(&b, 10);
    buf_write(&b, 20);
    buf_write(&b, 30);
    int val;
    buf_read(&b, &val);
    printf("Read: %d, Size: %d\n", val, buf_size(&b));
    return 0;
}
