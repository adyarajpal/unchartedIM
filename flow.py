from collections import deque
from typing import List, Tuple

def find_edges(edges: List[Tuple[int,int]], capacities: List[int],
               s: int, t: int) -> List[Tuple[int,int]]:
    class Edge:
        
        __slots__ = ('to', 'rev', 'capacity', 'original_capacity')
        
        def __init__(self, to: int, rev: int, capacity: int):
            self.to = to
            self.rev = rev   
            self.capacity = capacity
            self.original_capacity = capacity

    n = max( (max(u,v) for u,v in edges), default=max(s,t) ) + 1
    
    graph = [[] for _ in range(n)]

    forward_refs = []

    for (u,v), cap in zip(edges, capacities):
        fwd = Edge(v, len(graph[v]), cap)
        bck = Edge(u, len(graph[u]), 0)
        graph[u].append(fwd)
        graph[v].append(bck)
        fwd.rev = len(graph[v]) - 1
        bck.rev = len(graph[u]) - 1

        forward_refs.append(((u,v), fwd))


    level = [-1]*n

    def bfs_level_graph() -> bool:
        for i in range(n):
            level[i] = -1
        level[s] = 0
        queue = deque([s])
        
        while queue:
            u = queue.popleft()
            
            for e in graph[u]:
                
                if e.capacity > 0 and level[e.to] < 0:
                    level[e.to] = level[u] + 1
                    queue.append(e.to)
                    
        return level[t] >= 0

    def send_flow(u: int, flow_in: int, it: List[int]) -> int:
        if u == t:
            return flow_in
        
        while it[u] < len(graph[u]):
            e = graph[u][it[u]]
            
            if e.capacity > 0 and level[e.to] == level[u] + 1:
                pushed = send_flow(e.to, min(flow_in, e.capacity), it)
                
                if pushed > 0:
                    e.capacity -= pushed
                    graph[e.to][e.rev].capacity += pushed
                    
                    return pushed
            it[u] += 1
            
        return 0

    flow = 0
    
    while bfs_level_graph():
        it = [0]*n
        
        while True:
            pushed = send_flow(s, 10**14, it)
            
            if pushed <= 0:
                break
            flow += pushed


    result = []

    def can_push_one_more(edge_obj: Edge) -> bool:
        edge_obj.capacity += 1 
        visited = [False]*n
        queue2 = deque([s])
        visited[s] = True
        
        while queue2:
            u = queue2.popleft()
            
            if u == t:
                edge_obj.capacity -= 1
                return True
            
            for e in graph[u]:
                if e.capacity > 0 and not visited[e.to]:
                    visited[e.to] = True
                    queue2.append(e.to)
        edge_obj.capacity -= 1
        
        return False

    for ((u,v), fwd_edge) in forward_refs:
        
        if fwd_edge.original_capacity > 0 and fwd_edge.capacity == 0:
  
            if can_push_one_more(fwd_edge):
                result.append((u,v))

    return result

