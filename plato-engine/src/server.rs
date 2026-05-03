use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tower_http::cors::CorsLayer;

use crate::engine::PlatoEngine;
use crate::tile::{Provenance, Tile};

/// Shared application state.
pub struct AppState {
    pub engine: PlatoEngine,
}

/// Request body for submitting a tile.
#[derive(Debug, Deserialize)]
pub struct SubmitRequest {
    pub room_id: String,
    pub domain: String,
    pub question: String,
    pub answer: String,
    pub source: String,
    pub confidence: f64,
    #[serde(default)]
    pub tags: Vec<String>,
    pub provenance: ProvenanceInput,
}

#[derive(Debug, Deserialize)]
pub struct ProvenanceInput {
    pub agent_id: String,
    pub session_id: String,
    pub chain_hash: String,
    pub signature: String,
}

/// Response for tile submission.
#[derive(Debug, Serialize)]
pub enum SubmitResponse {
    Success { hash: String, room_id: String },
    Rejected { reason: String, tile_id: Option<uuid::Uuid> },
}

/// Query parameters for room listing.
#[derive(Debug, Deserialize)]
pub struct ListRoomsQuery {
    pub prefix: Option<String>,
}

/// Query parameters for tile query.
#[derive(Debug, Deserialize)]
pub struct QueryTilesQuery {
    pub tag: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

fn default_limit() -> usize {
    100
}

/// Build and return the Axum router.
pub fn build_router(state: Arc<AppState>) -> Router {
    let cors = CorsLayer::permissive();

    Router::new()
        .route("/submit", post(submit_tile))
        .route("/rooms", get(list_rooms))
        .route("/room/{id}", get(get_room))
        .route("/room/{id}/tiles", get(query_tiles))
        .route("/health", get(health))
        .route("/status", get(status))
        .layer(cors)
        .with_state(state)
}

async fn submit_tile(
    State(state): State<Arc<AppState>>,
    Json(req): Json<SubmitRequest>,
) -> impl IntoResponse {
    let tile = Tile {
        id: uuid::Uuid::new_v4(),
        domain: req.domain,
        question: req.question,
        answer: req.answer,
        source: req.source,
        confidence: req.confidence,
        tags: req.tags,
        created_at: chrono::Utc::now().timestamp(),
        provenance: Provenance {
            agent_id: req.provenance.agent_id,
            session_id: req.provenance.session_id,
            chain_hash: req.provenance.chain_hash,
            signature: req.provenance.signature,
        },
    };

    match state.engine.submit(&req.room_id, tile) {
        Ok(hash) => Json(SubmitResponse::Success {
            hash,
            room_id: req.room_id,
        })
        .into_response(),
        Err(rejection) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(SubmitResponse::Rejected {
                reason: rejection.reason,
                tile_id: rejection.tile_id,
            }),
        )
            .into_response(),
    }
}

async fn list_rooms(
    State(state): State<Arc<AppState>>,
    Query(params): Query<ListRoomsQuery>,
) -> impl IntoResponse {
    let rooms = state.engine.list_rooms(params.prefix.as_deref());
    Json(serde_json::json!({ "rooms": rooms }))
}

async fn get_room(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match state.engine.get_room(&id) {
        Some(room) => (StatusCode::OK, Json(room)).into_response(),
        None => (StatusCode::NOT_FOUND, Json(serde_json::json!({ "error": "room not found" }))).into_response(),
    }
}

async fn query_tiles(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Query(params): Query<QueryTilesQuery>,
) -> impl IntoResponse {
    let tiles = state.engine.query(&id, params.tag.as_deref(), params.limit);
    Json(serde_json::json!({ "tiles": tiles, "count": tiles.len() }))
}

async fn health(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let health = state.engine.health();
    Json(serde_json::json!({
        "status": "ok",
        "rooms": health.rooms_count,
        "tiles": health.tiles_count,
        "uptime_s": health.uptime_seconds,
    }))
}

async fn status(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let health = state.engine.health();
    Json(health)
}
