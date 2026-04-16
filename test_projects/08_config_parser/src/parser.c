#include "config.h"
#include <string.h>
#include <stdio.h>

int parse_line(const char *line) {
    char key[KEY_MAX], val[VAL_MAX];
    if (sscanf(line, "%63[^=]=%127s", key, val) != 2)
        return -1;
    return config_set(key, val);
}

int parse_file(const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) return -1;
    char buf[256];
    int ok = 0;
    while (fgets(buf, sizeof(buf), f)) {
        buf[strcspn(buf, "\n")] = 0;
        if (parse_line(buf) < 0) ok = -1;
    }
    fclose(f);
    return ok;
}
