#include "graph.h"
#include <string.h>

static int adj[NODE_MAX][NODE_MAX];
static int node_count = 0;

void graph_init(int n) {
    node_count = n;
    memset(adj, 0, sizeof(adj));
}

int graph_add_edge(int u, int v) {
    if (u < 0 || u >= node_count) return -1;
    if (v < 0 || v >= node_count) return -1;
    adj[u][v] = 1;
    return 0;
}

int graph_has_edge(int u, int v) {
    return adj[u][v];
}
