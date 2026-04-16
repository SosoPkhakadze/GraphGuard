#include <stddef.h>
#include <stdio.h>

int str_len(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

void str_reverse(char *s) {
    int len = str_len(s);
    int i = 0, j = len - 1;
    while (i < j) {
        char tmp = s[i];
        s[i] = s[j];
        s[j] = tmp;
        i++;
        j--;
    }
}

char *str_copy(char *dst, const char *src, int max) {
    if (!dst || !src) return dst;
    int i = 0;
    while (i < max - 1 && src[i]) {
        dst[i] = src[i];
        i++;
    }
    dst[i] = '\0';
    return dst;
}

void process_string(char *buf, int size) {
    str_copy(buf, buf, size);
    str_reverse(buf);
}

int main(void) {
    char s[16] = "hello";
    process_string(s, 16);
    printf("%s\n", s);
    return 0;
}
