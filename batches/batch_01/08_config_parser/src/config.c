#include "config.h"
#include <string.h>
#include <stdlib.h>

static ConfigEntry entries[CONFIG_MAX];
static int count = 0;

void config_init(void) {
    count = 0;
}

int config_set(const char *key, const char *value) {
    if (count >= CONFIG_MAX) return -1;
    strncpy(entries[count].key,   key,   KEY_MAX - 1);
    strncpy(entries[count].value, value, VAL_MAX - 1);
    count++;
    return 0;
}

const char *config_get(const char *key, const char *def) {
    for (int i = 0; i < count; i++) {
        if (strcmp(entries[i].key, key) == 0)
            return entries[i].value;
    }
    return def;
}

int config_has(const char *key) {
    return config_get(key, NULL) != NULL;
}
