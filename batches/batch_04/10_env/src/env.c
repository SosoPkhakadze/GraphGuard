#include <stdio.h>
#include <string.h>
#define EMAX 16
typedef struct { char k[64]; char v[128]; } EEntry;
typedef struct { EEntry e[EMAX]; int n; } Env;
void env_init(Env *s) { s->n=0; }
static void trim_end(char *s) {
    int i=strlen(s)-1;
    while(i>=0&&(s[i]==' '||s[i]=='\t'||s[i]=='\r'||s[i]=='\n')) s[i--]='\0';
}
int env_load(Env *s, const char *line) {
    if(s->n>=EMAX) return -1;
    const char *eq=strchr(line,'=');
    if(!eq) return -1;
    int kl=eq-line; if(kl>=64) return -1;
    strncpy(s->e[s->n].k,line,kl); s->e[s->n].k[kl]='\0';
    strncpy(s->e[s->n].v,eq+1,127);
    trim_end(s->e[s->n].v);
    s->n++; return 0;
}
const char *env_get(Env *s, const char *k, const char *def) {
    for(int i=0;i<s->n;i++) if(strcmp(s->e[i].k,k)==0) return s->e[i].v;
    return def;
}
int main(void) {
    Env s; env_init(&s);
    env_load(&s,"HOST=localhost  ");
    printf("HOST=[%s]\n", env_get(&s,"HOST","none"));
    return 0;
}
