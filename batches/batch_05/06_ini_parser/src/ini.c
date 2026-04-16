#include <stdio.h>
#include <string.h>
#define IMAX 16
typedef struct { char sec[32]; char k[64]; char v[128]; } IniE;
typedef struct { IniE e[IMAX]; int n; } Ini;
void ini_init(Ini *s) { s->n=0; }
int ini_load(Ini *s, const char *line, char *cur_sec) {
    if(line[0]=='['){
        int end=strcspn(line+1,"]");
        strncpy(cur_sec,line+1,end);
        cur_sec[end]='\0';
        return 0;
    }
    const char *eq=strchr(line,'=');
    if(!eq||s->n>=IMAX) return -1;
    IniE *e=&s->e[s->n++];
    strncpy(e->sec,cur_sec,31);
    int kl=eq-line; if(kl>=64)kl=63;
    strncpy(e->k,line,kl); e->k[kl]='\0';
    strncpy(e->v,eq+1,127);
    return 1;
}
const char *ini_get(Ini *s,const char *sec,const char *k,const char *def){
    for(int i=0;i<s->n;i++)
        if(strcmp(s->e[i].sec,sec)==0&&strcmp(s->e[i].k,k)==0) return s->e[i].v;
    return def;
}
int main(void) {
    Ini s; ini_init(&s); char sec[32]="";
    ini_load(&s,"[db]",sec); ini_load(&s,"host=localhost",sec);
    printf("host=[%s]\n", ini_get(&s,"db","host","none"));
    return 0;
}
