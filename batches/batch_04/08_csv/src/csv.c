#include <stdio.h>
#include <string.h>
typedef struct { const char *src; int pos; } CSV;
void csv_init(CSV *c, const char *src) { c->src=src; c->pos=0; }
int csv_next(CSV *c, char *out, int sz) {
    if(!c->src[c->pos]) return 0;
    int j=0;
    if(c->src[c->pos]=='"'){
        c->pos++;
        while(c->src[c->pos]&&c->src[c->pos]!='"'){
            if(j<sz-1) out[j++]=c->src[c->pos];
            c->pos++;
        }
        if(c->src[c->pos]=='"') c->pos++;
    } else {
        while(c->src[c->pos]&&c->src[c->pos]!=','){
            if(j<sz-1) out[j++]=c->src[c->pos];
            c->pos++;
        }
    }
    if(c->src[c->pos]==',') c->pos++;
    out[j]='\0'; return 1;
}
int csv_count(const char *line) {
    CSV c; csv_init(&c,line);
    char buf[256]; int n=0;
    while(csv_next(&c,buf,sizeof(buf))) n++;
    return n;
}
int main(void) {
    CSV c; csv_init(&c,"a,\"b,c\",d");
    char f[64];
    while(csv_next(&c,f,sizeof(f))) printf("[%s]\n",f);
    return 0;
}
