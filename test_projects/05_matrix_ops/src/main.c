#include "matrix.h"
#include <stdio.h>

void matrix_add(const Matrix *a, const Matrix *b, Matrix *out);
void matrix_scale(const Matrix *a, int factor, Matrix *out);
void matrix_transpose(const Matrix *a, Matrix *out);

int main(void) {
    Matrix a, b, c;
    matrix_init(&a, 2, 2);
    matrix_init(&b, 2, 2);
    matrix_set(&a, 0, 0, 1); matrix_set(&a, 0, 1, 2);
    matrix_set(&a, 1, 0, 3); matrix_set(&a, 1, 1, 4);
    matrix_set(&b, 0, 0, 5); matrix_set(&b, 0, 1, 6);
    matrix_set(&b, 1, 0, 7); matrix_set(&b, 1, 1, 8);
    matrix_add(&a, &b, &c);
    matrix_scale(&c, 2, &c);
    printf("c[0][0] = %d\n", matrix_get(&c, 0, 0));
    return 0;
}
