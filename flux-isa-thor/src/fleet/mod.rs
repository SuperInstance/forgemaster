pub mod coordinator;
pub mod i2i;

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

/// Fleet node descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetNode {
    pub id: String,
    pub hostname: String,
    pub role: NodeRole,
    pub gpu_available: bool,
    pub gpu_memory_mb: u32,
    pub status: NodeStatus,
    pub last_heartbeat: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeRole {
    Thor,
    Worker,
    Coordinator,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeStatus {
    Online,
    Busy,
    Offline,
    Draining,
}

/// Handle shared across VM and pipeline.
#[derive(Debug)]
pub struct FleetHandle {
    local_node: FleetNode,
    peers: Arc<RwLock<Vec<FleetNode>>>,
}

impl FleetHandle {
    pub fn new(local_node: FleetNode) -> Self {
        Self {
            local_node,
            peers: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub fn local_node(&self) -> &FleetNode {
        &self.local_node
    }

    pub async fn peers(&self) -> tokio::sync::RwLockReadGuard<'_, Vec<FleetNode>> {
        self.peers.read().await
    }

    pub async fn add_peer(&self, node: FleetNode) {
        self.peers.write().await.push(node);
    }

    pub async fn update_peer_status(&self, node_id: &str, status: NodeStatus) {
        let mut peers = self.peers.write().await;
        if let Some(peer) = peers.iter_mut().find(|p| p.id == node_id) {
            peer.status = status;
        }
    }
}
