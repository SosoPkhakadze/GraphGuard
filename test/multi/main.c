#include "math_utils.h"

int main() {
    int a = add(2, 3);
    int b = square(a);
    int c = multiply(b, add(1, 2));
    return c;
}
