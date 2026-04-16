#include <stdio.h>
#include <string.h>
int find_char(const char *s, char c) {
    for (int i=0; s[i]; i++) if (s[i]==c) return i;
    return -1;
}
int find_substr(const char *hay, const char *needle) {
    int hn=strlen(hay), nn=strlen(needle);
    for (int i=0; i <= hn-nn; i++)
        if (memcmp(hay+i, needle, nn)==0) return i;
    return -1;
}
int count_occur(const char *hay, const char *needle) {
    int count=0, nn=strlen(needle);
    for (int i=0; i<=(int)strlen(hay)-(int)nn; ) {
        int p = find_substr(hay+i, needle);
        if (p<0) break;
        count++; i+=p+nn;
    }
    return count;
}
int main(void) {
    printf("%d %d\n", find_substr("hello","lo"), count_occur("abab","ab"));
    return 0;
}
