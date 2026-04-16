#include <stdio.h>
#include "config.h"

int main() {
    config_init();
    config_set("host", "localhost");
    config_set("port", "8080");
    const char *host = config_get("host", "default");
    int has_port = config_has("port");
    printf("host=%s has_port=%d\n", host, has_port);
    return 0;
}
