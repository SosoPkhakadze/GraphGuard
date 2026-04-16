#include <stdio.h>
#include "graph.h"

int main() {
    graph_init(5);
    graph_add_edge(0, 1);
    graph_add_edge(1, 2);
    graph_add_edge(2, 3);
    int reachable = graph_has_path(0, 3);
    printf("0->3 reachable: %d\n", reachable);
    return 0;
}
