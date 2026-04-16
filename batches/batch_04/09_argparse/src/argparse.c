#include <stdio.h>
#include <string.h>
#define APMAX 8
typedef struct { const char *name; int found; } Arg;
typedef struct { Arg args[APMAX]; int n; } AP;
void ap_init(AP *p) { p->n=0; }
int ap_add(AP *p, const char *name) {
    if(p->n>=APMAX) return -1;
    p->args[p->n].name=name; p->args[p->n].found=0; p->n++;
    return 0;
}
int ap_parse(AP *p, int argc, char **argv) {
    for(int i=1;i<argc;i++){
        if(argv[i][0]!='-') continue;
        const char *flag=argv[i]+1;
        if(flag[0]=='-') flag++;
        for(int j=0;j<p->n;j++)
            if(strcmp(p->args[j].name,flag)==0) p->args[j].found=1;
    }
    return 0;
}
int ap_found(AP *p, const char *name) {
    for(int i=0;i<p->n;i++) if(strcmp(p->args[i].name,name)==0) return p->args[i].found;
    return 0;
}
int main(void) {
    AP p; ap_init(&p); ap_add(&p,"verbose");
    char *args[]={"prog","--verbose"};
    ap_parse(&p,2,args);
    printf("verbose=%d\n", ap_found(&p,"verbose"));
    return 0;
}
