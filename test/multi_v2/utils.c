#include "math_utils.h"

int square(int x) {
    x = clamp(x, -100, 100);
    return multiply(x, x);
}
