#include "graph.h"

static int visited[NODE_MAX];

int bfs(int start, int target) {
    int queue[NODE_MAX];
    int front = 0, back = 0;
    for (int i = 0; i < NODE_MAX; i++) visited[i] = 0;
    visited[start] = 1;
    queue[back++] = start;
    while (front < back) {
        int cur = queue[front++];
        if (cur == target) return 1;
        for (int i = 0; i < NODE_MAX; i++) {
            if (graph_has_edge(cur, i) && !visited[i]) {
                visited[i] = 1;
                queue[back++] = i;
            }
        }
    }
    return 0;
}

int graph_has_path(int start, int target) {
    return bfs(start, target);
}
