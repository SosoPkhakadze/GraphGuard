#include "matrix.h"

void matrix_add(const Matrix *a, const Matrix *b, Matrix *out) {
    matrix_init(out, a->rows, a->cols);
    for (int r = 0; r < a->rows; r++)
        for (int c = 0; c < a->cols; c++)
            matrix_set(out, r, c,
                       matrix_get(a, r, c) + matrix_get(b, r, c));
}

void matrix_scale(const Matrix *a, int factor, Matrix *out) {
    matrix_init(out, a->rows, a->cols);
    for (int r = 0; r < a->rows; r++)
        for (int c = 0; c < a->cols; c++)
            matrix_set(out, r, c, matrix_get(a, r, c) * factor);
}

void matrix_transpose(const Matrix *a, Matrix *out) {
    matrix_init(out, a->cols, a->rows);
    for (int r = 0; r < a->rows; r++)
        for (int c = 0; c < a->cols; c++)
            matrix_set(out, c, r, matrix_get(a, r, c));
}
