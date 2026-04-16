#ifndef MATRIX_H
#define MATRIX_H

#define MAT_MAX 8

typedef struct {
    int rows;
    int cols;
    int data[MAT_MAX][MAT_MAX];
} Matrix;

void matrix_init(Matrix *m, int rows, int cols);
int  matrix_get(const Matrix *m, int r, int c);
void matrix_set(Matrix *m, int r, int c, int val);
void matrix_zero(Matrix *m);

#endif
