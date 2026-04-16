#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

int divide(int a, int b) {
    if (b == 0) {
        return 0;
    }
    return a / b;
}

int main(void) {
    int x = add(10, 5);
    int y = divide(x, 0);
    printf("%d\n", y);
    return 0;
}
