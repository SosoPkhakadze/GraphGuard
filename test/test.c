#include <stdio.h>

int A() {
    return 1;
}

int B() {
    return A();
}

int main() {
    return B();
}