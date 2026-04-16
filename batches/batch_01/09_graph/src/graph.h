#ifndef GRAPH_H
#define GRAPH_H

#define NODE_MAX 32

void graph_init(int n);
int  graph_add_edge(int u, int v);
int  graph_has_edge(int u, int v);
int  bfs(int start, int target);
int  graph_has_path(int start, int target);

#endif
