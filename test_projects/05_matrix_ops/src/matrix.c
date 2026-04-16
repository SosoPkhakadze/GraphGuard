#include "matrix.h"

void matrix_init(Matrix *m, int rows, int cols) {
    m->rows = rows;
    m->cols = cols;
}

int matrix_get(const Matrix *m, int r, int c) {
    if (r < 0 || r >= m->rows || c < 0 || c >= m->cols) return 0;
    return m->data[r][c];
}

void matrix_set(Matrix *m, int r, int c, int val) {
    if (r < 0 || r >= m->rows || c < 0 || c >= m->cols) return;
    m->data[r][c] = val;
}

void matrix_zero(Matrix *m) {
    for (int r = 0; r < m->rows; r++)
        for (int c = 0; c < m->cols; c++)
            matrix_set(m, r, c, 0);
}
