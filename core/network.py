"""
Network Graph Manager for the simulated routing environment.
"""

import heapq
from typing import Dict, List, Tuple, Optional, Set
from .node import Node
from .link import Link


class Network:
    """Represents the complete network topology of nodes and links."""

    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.links: Dict[Tuple[int, int], Link] = {}
        self.positions: Dict[int, Tuple[float, float]] = {}  # 2D coordinates for visualization

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)

    @property
    def num_links(self) -> int:
        return len(self.links)

    def add_node(
        self,
        node_id: int,
        buffer_capacity: int = 25,
        name: Optional[str] = None,
        pos: Optional[Tuple[float, float]] = None
    ) -> Node:
        """Add a router node to the network."""
        if node_id in self.nodes:
            return self.nodes[node_id]
        
        node = Node(node_id=node_id, buffer_capacity=buffer_capacity, name=name)
        self.nodes[node_id] = node
        if pos is not None:
            self.positions[node_id] = pos
        return node

    def add_link(
        self,
        u: int,
        v: int,
        bandwidth: float = 10.0,
        propagation_delay: float = 0.05,
        drop_probability: float = 0.0
    ) -> Link:
        """Create a bidirectional link between nodes u and v."""
        if u not in self.nodes:
            self.add_node(u)
        if v not in self.nodes:
            self.add_node(v)

        link_key = (min(u, v), max(u, v))
        if link_key in self.links:
            return self.links[link_key]

        link = Link(
            node_a=u,
            node_b=v,
            bandwidth=bandwidth,
            propagation_delay=propagation_delay,
            drop_probability=drop_probability
        )
        self.links[link_key] = link

        # Attach link to both adjacent nodes
        self.nodes[u].add_link(v, link)
        self.nodes[v].add_link(u, link)
        return link

    def get_link(self, u: int, v: int) -> Optional[Link]:
        """Retrieve the link between u and v if it exists."""
        link_key = (min(u, v), max(u, v))
        return self.links.get(link_key)

    def kill_link(self, u: int, v: int, current_time: float = 0.0) -> bool:
        """Simulate a physical link cut."""
        link = self.get_link(u, v)
        if link and link.is_up:
            link.set_down(current_time)
            return True
        return False

    def restore_link(self, u: int, v: int, current_time: float = 0.0) -> bool:
        """Restore a previously cut link."""
        link = self.get_link(u, v)
        if link and not link.is_up:
            link.set_up(current_time)
            return True
        return False

    def get_active_neighbors(self, node_id: int) -> List[int]:
        """Get neighboring nodes accessible via links currently UP."""
        if node_id not in self.nodes:
            return []
        return self.nodes[node_id].active_neighbors

    def dijkstra_shortest_paths(
        self,
        src: int,
        cost_metric: str = "delay"
    ) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
        """
        Pure Python Dijkstra algorithm.
        Returns:
            distances: mapping dst_node -> minimum cost
            predecessors: mapping dst_node -> previous node along optimal path
        """
        distances: Dict[int, float] = {nid: float('inf') for nid in self.nodes}
        predecessors: Dict[int, Optional[int]] = {nid: None for nid in self.nodes}
        distances[src] = 0.0
        
        pq = [(0.0, src)]

        while pq:
            curr_dist, u = heapq.heappop(pq)
            if curr_dist > distances[u]:
                continue

            for v in self.get_active_neighbors(u):
                link = self.get_link(u, v)
                if not link or not link.is_up:
                    continue

                if cost_metric == "hops":
                    cost = 1.0
                elif cost_metric == "delay":
                    cost = link.total_link_delay
                elif cost_metric == "congestion":
                    queue_delay = self.nodes[v].estimate_queue_delay(u)
                    cost = link.total_link_delay + queue_delay
                else:
                    cost = link.total_link_delay

                new_dist = curr_dist + cost
                if new_dist < distances[v]:
                    distances[v] = new_dist
                    predecessors[v] = u
                    heapq.heappush(pq, (new_dist, v))

        return distances, predecessors

    def get_shortest_path_next_hop(self, src: int, dst: int, cost_metric: str = "delay") -> Optional[int]:
        """Return the optimal next hop node from src to dst using Dijkstra."""
        if src == dst:
            return src
        
        distances, predecessors = self.dijkstra_shortest_paths(src, cost_metric=cost_metric)
        if distances[dst] == float('inf'):
            return None  # Unreachable

        # Reconstruct path backwards from dst to src
        curr = dst
        prev = None
        while curr is not None and curr != src:
            prev = curr
            curr = predecessors[curr]

        return prev if curr == src else None

    def is_connected(self) -> bool:
        """Check if all nodes in the network are mutually reachable via active links."""
        if not self.nodes:
            return True
        start_node = next(iter(self.nodes))
        visited: Set[int] = set()
        queue = [start_node]
        visited.add(start_node)

        while queue:
            curr = queue.pop(0)
            for neighbor in self.get_active_neighbors(curr):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == len(self.nodes)

    def reset_network_state(self):
        """Reset all nodes, queues, and links to initial clean state."""
        for node in self.nodes.values():
            node.reset_stats()
        for link in self.links.values():
            link.packets_transmitted = 0
            link.packets_dropped = 0
            link.is_up = True

