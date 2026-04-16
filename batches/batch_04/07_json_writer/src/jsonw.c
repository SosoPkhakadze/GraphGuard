#include <stdio.h>
#include <string.h>
#define JWCAP 256
typedef struct { char buf[JWCAP]; int pos; } JW;
void jw_init(JW *w) { w->pos=0; w->buf[0]='\0'; }
static int jw_raw(JW *w, const char *s) {
    int n=strlen(s);
    if(w->pos+n>=JWCAP) return -1;
    memcpy(w->buf+w->pos,s,n); w->pos+=n; w->buf[w->pos]='\0';
    return n;
}
int jw_string(JW *w, const char *s) {
    jw_raw(w,"\"");
    while(*s){
        if(*s=='"') jw_raw(w,"\\"");
        else if(*s=='\\') jw_raw(w,"\\\\");
        else { char c[2]={*s,0}; jw_raw(w,c); }
        s++;
    }
    return jw_raw(w,"\"");
}
int jw_int(JW *w, int v) { char t[32]; sprintf(t,"%d",v); return jw_raw(w,t); }
const char *jw_get(JW *w) { return w->buf; }
int main(void) {
    JW w; jw_init(&w);
    jw_raw(&w,"{\"k\":"); jw_string(&w,"hel\"lo"); jw_raw(&w,"}");
    printf("%s\n", jw_get(&w));
    return 0;
}
