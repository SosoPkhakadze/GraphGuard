#ifndef CONFIG_H
#define CONFIG_H

#define CONFIG_MAX 64
#define KEY_MAX    64
#define VAL_MAX   128

typedef struct {
    char key[KEY_MAX];
    char value[VAL_MAX];
} ConfigEntry;

void        config_init(void);
int         config_set(const char *key, const char *value);
const char *config_get(const char *key, const char *def);
int         config_has(const char *key);

#endif
