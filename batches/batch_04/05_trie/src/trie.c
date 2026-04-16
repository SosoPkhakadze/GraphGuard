#include <stdio.h>
#include <string.h>
#define ALPHA 26
#define TNODES 128
typedef struct { int ch[ALPHA]; int end; } TNode;
typedef struct { TNode nodes[TNODES]; int n; } Trie;
void trie_init(Trie *t) {
    memset(t->nodes[0].ch,-1,sizeof(t->nodes[0].ch));
    t->nodes[0].end=0; t->n=1;
}
int trie_insert(Trie *t, const char *s) {
    int cur=0;
    while(*s){
        int c=*s-'a';
        if(t->nodes[cur].ch[c]<0){
            if(t->n>=TNODES) return -1;
            memset(t->nodes[t->n].ch,-1,sizeof(t->nodes[t->n].ch));
            t->nodes[t->n].end=0;
            t->nodes[cur].ch[c]=t->n++;
        }
        cur=t->nodes[cur].ch[c]; s++;
    }
    t->nodes[cur].end=1; return 0;
}
int trie_search(Trie *t, const char *s) {
    int cur=0;
    while(*s){ int c=*s-'a'; if(t->nodes[cur].ch[c]<0) return 0; cur=t->nodes[cur].ch[c]; s++; }
    return t->nodes[cur].end;
}
int main(void) {
    Trie t; trie_init(&t);
    trie_insert(&t,"hello");
    printf("hello=%d world=%d\n", trie_search(&t,"hello"), trie_search(&t,"world"));
    return 0;
}
