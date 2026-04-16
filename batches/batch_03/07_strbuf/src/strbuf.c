#include <stdio.h>
#include <string.h>
#define SB_CAP 128
typedef struct { char d[SB_CAP]; int len; } StrBuf;
void sb_init(StrBuf *s) { s->len=0; s->d[0]='\0'; }
int sb_append(StrBuf *s, const char *str) {
    int n=strlen(str);
    if(s->len+n >= SB_CAP) return -1;
    memcpy(s->d+s->len, str, n);
    s->len+=n; s->d[s->len]='\0';
    return n;
}
int sb_len(StrBuf *s) { return s->len; }
void sb_clear(StrBuf *s) { s->len=0; s->d[0]='\0'; }
const char *sb_str(StrBuf *s) { return s->d; }
int main(void) {
    StrBuf sb; sb_init(&sb);
    sb_append(&sb,"hello"); sb_append(&sb," world");
    printf("[%s] len=%d\n", sb_str(&sb), sb_len(&sb));
    return 0;
}
