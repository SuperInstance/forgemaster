use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{debug, info};
use uuid::Uuid;

use super::i2i::{I2iMessage, I2iType};
use super::{FleetHandle, NodeStatus};

/// Task assigned to a fleet node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetTask {
    pub id: Uuid,
    pub task_type: String,
    pub payload: Vec<u8>,
    pub priority: u8,
    pub deadline: Option<u64>,
    pub assigned_to: Option<String>,
    pub status: TaskStatus,
    pub created_at: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    Assigned,
    Running,
    Completed,
    Failed,
    TimedOut,
}

/// Coordinates task distribution across fleet nodes.
pub struct FleetCoordinator {
    handle: Arc<FleetHandle>,
    task_queue: Arc<RwLock<Vec<FleetTask>>>,
    heartbeat_interval: Duration,
}

impl FleetCoordinator {
    pub fn new(handle: Arc<FleetHandle>, heartbeat_interval: Duration) -> Self {
        Self {
            handle,
            task_queue: Arc::new(RwLock::new(Vec::new())),
            heartbeat_interval,
        }
    }

    /// Submit a task to the fleet queue.
    pub async fn submit_task(&self, task: FleetTask) {
        let mut queue = self.task_queue.write().await;
        // Insert sorted by priority (highest first)
        let pos = queue
            .iter()
            .position(|t| t.priority < task.priority)
            .unwrap_or(queue.len());
        queue.insert(pos, task);
        info!("Task queued");
    }

    /// Assign pending tasks to available nodes.
    pub async fn assign_tasks(&self) -> Vec<FleetTask> {
        let mut queue = self.task_queue.write().await;
        let peers = self.handle.peers().await;
        let available: Vec<_> = peers
            .iter()
            .filter(|p| p.status == NodeStatus::Online)
            .collect();

        let mut assigned = Vec::new();
        let mut node_idx = 0;

        for task in queue.iter_mut() {
            if task.status != TaskStatus::Pending {
                continue;
            }
            if available.is_empty() {
                break;
            }
            let node = &available[node_idx % available.len()];
            task.assigned_to = Some(node.id.clone());
            task.status = TaskStatus::Assigned;
            assigned.push(task.clone());
            node_idx += 1;
        }

        assigned
    }

    /// Mark a task as completed.
    pub async fn complete_task(&self, task_id: Uuid, _result: &[u8]) {
        let mut queue = self.task_queue.write().await;
        if let Some(task) = queue.iter_mut().find(|t| t.id == task_id) {
            task.status = TaskStatus::Completed;
            info!("Task {} completed", task_id);
        }
    }

    /// Broadcast heartbeat to fleet.
    pub async fn broadcast_heartbeat(&self) {
        let node = self.handle.local_node();
        let _msg = I2iMessage {
            msg_type: I2iType::Status,
            from: node.id.clone(),
            payload: serde_json::to_vec(&node).unwrap_or_default(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        };
        debug!("Heartbeat from {}", node.id);
        // In production: send to all peers via gRPC
    }

    /// Get pending task count.
    pub async fn pending_count(&self) -> usize {
        self.task_queue
            .read()
            .await
            .iter()
            .filter(|t| t.status == TaskStatus::Pending)
            .count()
    }

    /// Start periodic heartbeat loop.
    pub async fn run_heartbeat_loop(self: Arc<Self>) {
        let interval = self.heartbeat_interval;
        loop {
            self.broadcast_heartbeat().await;
            tokio::time::sleep(interval).await;
        }
    }
}
