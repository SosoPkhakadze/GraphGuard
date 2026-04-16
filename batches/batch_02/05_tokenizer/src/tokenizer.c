#include <stdio.h>
#include <string.h>
typedef struct { const char *src; int pos; int len; } Tok;
void tok_init(Tok *t, const char *src) { t->src=src; t->pos=0; t->len=strlen(src); }
int tok_next(Tok *t, char *out, int sz) {
    while (t->pos < t->len && t->src[t->pos]==' ') t->pos++;
    if (t->pos >= t->len) return 0;
    int start = t->pos;
    while (t->pos < t->len && t->src[t->pos]!=' ') t->pos++;
    int n = t->pos - start;
    if (n >= sz) n = sz - 1;
    memcpy(out, t->src + start, n);
    out[n] = '\0';
    return n;
}
int tok_has_more(Tok *t) { return t->pos < t->len; }
int main(void) {
    Tok t; tok_init(&t, "hello world");
    char buf[32];
    while (tok_next(&t, buf, sizeof(buf)))
        printf("[%s]\n", buf);
    return 0;
}
