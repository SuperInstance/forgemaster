use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};

use crate::merkle::{Leaf, LeafData, VerificationTrace};
use crate::store::ProvenanceStore;

#[derive(Clone)]
pub struct AppState {
    pub store: std::sync::Arc<ProvenanceStore>,
}

#[derive(Debug, Deserialize)]
pub struct SubmitRequest {
    pub trace: Vec<String>,
    pub domain: String,
    pub confidence: f64,
    pub source: String,
}

#[derive(Debug, Serialize)]
pub struct SubmitResponse {
    pub leaf_hash: String,
    pub merkle_root: String,
    pub tree_size: usize,
    pub proof_path: Vec<crate::merkle::ProofElement>,
}

#[derive(Debug, Serialize)]
pub struct VerifyResponse {
    pub valid: bool,
    pub leaf_hash: String,
    pub merkle_root: String,
    pub proof_path: Vec<crate::merkle::ProofElement>,
}

#[derive(Debug, Serialize)]
pub struct RootResponse {
    pub merkle_root: String,
}

#[derive(Debug, Serialize)]
pub struct TreeResponse {
    pub index: u64,
    pub root: String,
    pub leaf_count: usize,
    pub leaves: Vec<LeafInfo>,
}

#[derive(Debug, Serialize)]
pub struct LeafInfo {
    pub hash: String,
    pub domain: String,
    pub confidence: f64,
    pub source: String,
}

#[derive(Debug, Serialize)]
pub struct StatsResponse {
    pub total_leaves: usize,
    pub sealed_trees: u64,
    pub db_size_bytes: u64,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/submit", post(submit))
        .route("/verify/:leaf_hash", get(verify))
        .route("/root", get(root))
        .route("/tree/:index", get(get_tree))
        .route("/stats", get(stats))
        .with_state(state)
}

async fn submit(
    State(state): State<AppState>,
    Json(req): Json<SubmitRequest>,
) -> impl IntoResponse {
    let leaf = Leaf::new(LeafData::Verification(VerificationTrace {
        trace: req.trace,
        domain: req.domain,
        confidence: req.confidence,
        source: req.source,
    }));

    match state.store.add_leaf(leaf) {
        Ok(result) => (
            StatusCode::OK,
            Json(SubmitResponse {
                leaf_hash: result.leaf_hash,
                merkle_root: result.merkle_root,
                tree_size: result.tree_size,
                proof_path: result.proof_path,
            }),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse { error: e }),
        )
            .into_response(),
    }
}

async fn verify(
    State(state): State<AppState>,
    Path(leaf_hash): Path<String>,
) -> impl IntoResponse {
    match state.store.verify_leaf(&leaf_hash) {
        Some(result) => (
            StatusCode::OK,
            Json(VerifyResponse {
                valid: result.valid,
                leaf_hash: result.leaf_hash,
                merkle_root: result.merkle_root,
                proof_path: result.proof_path,
            }),
        )
            .into_response(),
        None => (
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                error: format!("leaf not found: {}", leaf_hash),
            }),
        )
            .into_response(),
    }
}

async fn root(State(state): State<AppState>) -> impl IntoResponse {
    Json(RootResponse {
        merkle_root: state.store.current_root(),
    })
}

async fn get_tree(
    State(state): State<AppState>,
    Path(index): Path<u64>,
) -> impl IntoResponse {
    match state.store.get_tree(index) {
        Some(tree) => {
            let root = tree.root.clone();
            let leaf_count = tree.size();
            let leaves: Vec<LeafInfo> = tree
                .leaves
                .iter()
                .map(|l| match &l.data {
                    LeafData::Verification(v) => LeafInfo {
                        hash: l.hash.clone(),
                        domain: v.domain.clone(),
                        confidence: v.confidence,
                        source: v.source.clone(),
                    },
                    LeafData::Constraint(c) => LeafInfo {
                        hash: l.hash.clone(),
                        domain: c.constraint_id.clone(),
                        confidence: 1.0,
                        source: c.status.clone(),
                    },
                })
                .collect();

            (
                StatusCode::OK,
                Json(TreeResponse {
                    index: tree.index,
                    root,
                    leaf_count,
                    leaves,
                }),
            )
                .into_response()
        }
        None => (
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                error: format!("tree not found: {}", index),
            }),
        )
            .into_response(),
    }
}

async fn stats(State(state): State<AppState>) -> impl IntoResponse {
    let s = state.store.stats();
    Json(StatsResponse {
        total_leaves: s.total_leaves,
        sealed_trees: s.sealed_trees,
        db_size_bytes: s.db_size_bytes,
    })
}
