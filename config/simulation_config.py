"""
Simulation and Reinforcement Learning Configuration Parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class RLConfig:
    """Hyperparameters for Reinforcement Learning based routing agents."""
    learning_rate: float = 0.15          # Alpha: Learning rate
    discount_factor: float = 0.90        # Gamma: Discount factor
    epsilon: float = 0.15                # Exploration probability
    epsilon_min: float = 0.01            # Minimum exploration probability
    epsilon_decay: float = 0.998         # Decay rate per simulation step / episode
    confidence_decay: float = 0.95       # For CQ-Routing / Dual Q-Routing confidence updates
    queue_weight: float = 1.0            # Weight of queue delay penalty in cost estimation
    link_weight: float = 1.0             # Weight of link transmission/propagation delay


@dataclass
class NetworkConfig:
    """Network topology and hardware simulation parameters."""
    buffer_capacity: int = 25            # Maximum packets in node queue before drop
    default_bandwidth: float = 10.0      # Packets per second transmission rate
    default_prop_delay: float = 0.05     # Propagation delay per link in seconds
    link_drop_probability: float = 0.001 # Random packet loss probability on link
    ttl_limit: int = 64                  # Time-To-Live (hop count limit to prevent infinite loops)


@dataclass
class TrafficConfig:
    """Traffic generation configuration."""
    packet_rate: float = 15.0            # Total packets injected per second
    traffic_pattern: str = "uniform"     # "uniform", "hotspot", "bursty", "pareto"
    burst_multiplier: float = 3.5        # Traffic spike multiplier during bursts
    burst_interval: float = 20.0         # Seconds between traffic bursts
    burst_duration: float = 5.0          # Duration of burst in seconds
    hotspot_nodes: list = field(default_factory=lambda: [0, 5])  # Target nodes for hotspot traffic


@dataclass
class SimulationConfig:
    """Master simulation configuration."""
    duration: float = 100.0              # Simulation time in seconds
    seed: int = 42                       # Random seed for reproducibility
    rl: RLConfig = field(default_factory=RLConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration": self.duration,
            "seed": self.seed,
            "rl": self.rl.__dict__,
            "network": self.network.__dict__,
            "traffic": self.traffic.__dict__
        }

