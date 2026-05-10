"""
elevation_operators.py — Level elevation transforms for neural networks

When the saturation detector signals qualitative exhaustion, these operators
perform the architectural transformation to the next hyperoperational level.

H₀ → H₁: Add sequence processing (recurrent/attention layers)
H₁ → H₂: Add structural processing (graph/tree constructors)
H₂ → H₃: Add topological processing (persistent homology features)
H₃ → H₄: Add representation space restructuring (meta-learning)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple


class ElevateH0toH1(nn.Module):
    """
    Elevate from token-level (H₀) to sequence-level (H₁) processing.

    Adds a self-attention layer on top of token embeddings so the model
    can accumulate information across token positions.
    """

    def __init__(self, embed_dim: int, num_heads: int = 2, max_seq_len: int = 64):
        super().__init__()
        self.embed_dim = embed_dim
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.norm = nn.LayerNorm(embed_dim)
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 2),
            nn.ReLU(),
            nn.Linear(embed_dim * 2, embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, embed_dim) or (batch, features)
        if x.dim() == 2:
            x = x.unsqueeze(1)  # treat as sequence of length 1

        attn_out, _ = self.attention(x, x, x)
        x = self.norm(x + attn_out)
        x = x + self.ffn(x)
        return x


class ElevateH1toH2(nn.Module):
    """
    Elevate from sequence-level (H₁) to structure-level (H₂) processing.

    Adds a graph constructor that treats positions as nodes and builds
    adjacency from attention similarity, then runs a GCN-like layer.
    """

    def __init__(self, embed_dim: int, k_neighbors: int = 3):
        super().__init__()
        self.k = k_neighbors
        self.graph_conv = nn.Linear(embed_dim * 2, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)

    def build_adjacency(self, x: torch.Tensor) -> torch.Tensor:
        """Build k-nearest-neighbor adjacency from representation similarity."""
        # x: (batch, seq_len, embed_dim)
        batch_size, seq_len, _ = x.shape
        adj = torch.zeros(batch_size, seq_len, seq_len, device=x.device)

        for b in range(batch_size):
            # Cosine similarity between all pairs
            norms = F.normalize(x[b], dim=-1)
            sim = torch.mm(norms, norms.t())

            # Keep top-k neighbors
            k = min(self.k, seq_len - 1)
            if k > 0:
                _, topk_idx = sim.topk(k + 1, dim=-1)
                for i in range(seq_len):
                    for j in topk_idx[i]:
                        if i != j:
                            adj[b, i, j] = sim[i, j]
                            adj[b, j, i] = sim[i, j]

        return adj

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            x = x.unsqueeze(1)

        batch_size, seq_len, embed_dim = x.shape

        # Build adjacency
        adj = self.build_adjacency(x)

        # Graph convolution: aggregate neighbor information
        # For each node, concatenate self with neighbor mean
        neighbor_sum = torch.bmm(adj, x)  # (batch, seq_len, embed_dim)
        neighbor_count = adj.sum(dim=-1, keepdim=True).clamp(min=1)
        neighbor_mean = neighbor_sum / neighbor_count

        combined = torch.cat([x, neighbor_mean], dim=-1)
        out = self.graph_conv(combined)
        out = self.norm(x + out)

        return out


class ElevateH2toH3(nn.Module):
    """
    Elevate from structure-level (H₂) to topology-level (H₃) processing.

    Adds topological features derived from the representation's
    pairwise distance matrix (a proxy for persistent homology).
    """

    def __init__(self, embed_dim: int, n_topology_features: int = 8):
        super().__init__()
        self.n_topo_features = n_topology_features
        self.topo_proj = nn.Linear(n_topology_features, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)

    def compute_topology_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute simple topological features from representation matrix.

        These are proxies for Betti numbers and persistent homology:
        1. Connectivity ratio (fraction of connected pairs)
        2. Number of connected components (via union-find)
        3. Average clustering coefficient
        4. Graph diameter (approximate)
        5-8. Distance distribution statistics
        """
        batch_size, seq_len, embed_dim = x.shape
        features = []

        for b in range(batch_size):
            # Pairwise distance matrix
            diffs = x[b].unsqueeze(0) - x[b].unsqueeze(1)  # (seq, seq, embed)
            dists = torch.norm(diffs, dim=-1)  # (seq, seq)

            # Threshold for connectivity
            threshold = dists.median()
            connected = (dists < threshold).float()
            # Remove self-connections
            eye = torch.eye(seq_len, device=x.device)
            connected = connected * (1 - eye)

            # Feature 1: Connectivity ratio
            conn_ratio = connected.sum() / max(seq_len * (seq_len - 1), 1)

            # Feature 2: Approximate connected components (simple BFS)
            visited = torch.zeros(seq_len, dtype=torch.bool, device=x.device)
            n_components = 0
            adj = connected > 0
            for start in range(seq_len):
                if visited[start]:
                    continue
                n_components += 1
                queue = [start]
                visited[start] = True
                while queue:
                    node = queue.pop(0)
                    neighbors = adj[node].nonzero(as_tuple=True)[0]
                    for nb in neighbors:
                        if not visited[nb]:
                            visited[nb] = True
                            queue.append(nb.item())

            # Feature 3: Average degree
            avg_degree = connected.sum(dim=1).mean()

            # Feature 4-8: Distance statistics
            triu_dists = dists[torch.triu(torch.ones(seq_len, seq_len, device=x.device) == 1)]
            if triu_dists.numel() > 0:
                dist_mean = triu_dists.mean()
                dist_std = triu_dists.std()
                dist_min = triu_dists.min()
                dist_max = triu_dists.max()
            else:
                dist_mean = dist_std = dist_min = dist_max = torch.tensor(0.0, device=x.device)

            # Pad to n_topology_features
            feat = torch.stack([
                conn_ratio,
                torch.tensor(n_components, dtype=torch.float, device=x.device) / max(seq_len, 1),
                avg_degree / max(seq_len, 1),
                dist_mean,
                dist_std,
                dist_min,
                dist_max,
                torch.tensor(0.0, device=x.device),
            ])
            features.append(feat)

        return torch.stack(features)  # (batch, n_topology_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            x = x.unsqueeze(1)

        topo_features = self.compute_topology_features(x)  # (batch, n_topo)
        # Project to embed_dim and add to all positions
        topo_signal = self.topo_proj(topo_features)  # (batch, embed_dim)
        topo_signal = topo_signal.unsqueeze(1).expand_as(x)

        out = self.norm(x + topo_signal)
        return out


# ---- Simple test models for delta-detect experiments ----

class SimpleH0Model(nn.Module):
    """Token-level model: linear projection, no sequence processing."""
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.encoder = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.decoder = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.relu(self.encoder(x))
        return self.decoder(x)


class SimpleH1Model(nn.Module):
    """Sequence-level model: adds attention on top of H₀."""
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.encoder = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.elevation = ElevateH0toH1(hidden_dim, num_heads=2)
        self.decoder = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.relu(self.encoder(x))
        x = self.elevation(x.unsqueeze(1) if x.dim() == 2 else x)
        if x.dim() == 3:
            x = x.mean(dim=1)  # pool over sequence
        return self.decoder(x)


class SimpleH2Model(nn.Module):
    """Structure-level model: adds graph construction on top of H₁."""
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.encoder = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.elevation1 = ElevateH0toH1(hidden_dim, num_heads=2)
        self.elevation2 = ElevateH1toH2(hidden_dim, k_neighbors=3)
        self.decoder = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.relu(self.encoder(x))
        x = x.unsqueeze(1) if x.dim() == 2 else x
        x = self.elevation1(x)
        x = self.elevation2(x)
        if x.dim() == 3:
            x = x.mean(dim=1)
        return self.decoder(x)
