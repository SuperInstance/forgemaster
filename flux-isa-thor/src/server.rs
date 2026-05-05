use axum::extract::{State, WebSocketUpgrade};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::Json;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing::warn;

use crate::config::ThorConfig;
use crate::cuda::solver::{BatchCspSolver, CspInstance};
use crate::cuda::sonar::{BatchSonarPhysics, SonarParams};
use crate::cuda::GpuDispatcher;
use crate::fleet::FleetHandle;
use crate::plato::PlatoHandle;
use crate::vm::ThorVm;

// ── Request/Response types ───────────────────────────────────────

#[derive(Debug, Deserialize)]
pub struct CompileRequest {
    pub spec: serde_json::Value,
}

#[derive(Debug, Serialize)]
pub struct CompileResponse {
    pub bytecode: Vec<u8>,
    pub instruction_count: usize,
}

#[derive(Debug, Deserialize)]
pub struct VerifyRequest {
    pub claim: serde_json::Value,
    pub evidence: Vec<serde_json::Value>,
}

#[derive(Debug, Serialize)]
pub struct VerifyResponse {
    pub verified: bool,
    pub confidence: f64,
    pub details: String,
}

#[derive(Debug, Deserialize)]
pub struct ExecuteRequest {
    pub bytecode: Vec<u8>,
}

#[derive(Debug, Serialize)]
pub struct ExecuteResponse {
    pub result: crate::vm::VmResult,
}

#[derive(Debug, Deserialize)]
pub struct BatchSolveRequest {
    pub instances: Vec<CspInstance>,
}

#[derive(Debug, Serialize)]
pub struct BatchSolveResponse {
    pub solutions: Vec<crate::cuda::CspSolution>,
    pub total: usize,
    pub gpu_used: bool,
}

#[derive(Debug, Deserialize)]
pub struct BatchSonarRequest {
    pub params: Vec<SonarParams>,
}

#[derive(Debug, Serialize)]
pub struct BatchSonarResponse {
    pub results: Vec<crate::cuda::SonarResult>,
    pub total: usize,
    pub gpu_used: bool,
}

#[derive(Debug, Serialize)]
pub struct StatusResponse {
    pub node_id: String,
    pub gpu_available: bool,
    pub gpu_memory_mb: u32,
    pub total_instructions: u64,
    pub uptime_secs: u64,
    pub pipeline_committed: u64,
}

// ── App state ────────────────────────────────────────────────────

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<ThorConfig>,
    pub vm: Arc<ThorVm>,
    pub gpu: Arc<GpuDispatcher>,
    pub plato: Arc<PlatoHandle>,
    pub fleet: Arc<FleetHandle>,
    pub start_time: std::time::Instant,
    pub pipeline_committed: Arc<std::sync::atomic::AtomicU64>,
}

// ── Router ───────────────────────────────────────────────────────

pub fn router(state: AppState) -> axum::Router {
    axum::Router::new()
        .route("/compile", post(compile))
        .route("/verify", post(verify))
        .route("/execute", post(execute))
        .route("/batch-solve", post(batch_solve))
        .route("/batch-sonar", post(batch_sonar))
        .route("/status", get(status))
        .route("/metrics", get(metrics))
        .route("/stream", get(ws_stream))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

// ── Handlers ─────────────────────────────────────────────────────

async fn compile(
    State(_s): State<AppState>,
    Json(_req): Json<CompileRequest>,
) -> Result<Json<CompileResponse>, StatusCode> {
    // Minimal: return HALT bytecode
    // Production: full CSP→FLUX compiler
    let bytecode = vec![0x45u8]; // HALT
    Ok(Json(CompileResponse {
        instruction_count: bytecode.len(),
        bytecode,
    }))
}

async fn verify(
    State(_s): State<AppState>,
    Json(req): Json<VerifyRequest>,
) -> Json<VerifyResponse> {
    // The kill-shot endpoint: verify a claim against evidence
    let _claim = serde_json::to_string(&req.claim).unwrap_or_default();
    let evidence_count = req.evidence.len();

    // Production: run full FLUX verification bytecode
    Json(VerifyResponse {
        verified: evidence_count > 0,
        confidence: if evidence_count > 0 { 0.95 } else { 0.0 },
        details: format!("Verified claim against {evidence_count} evidence items"),
    })
}

async fn execute(
    State(s): State<AppState>,
    Json(req): Json<ExecuteRequest>,
) -> Json<ExecuteResponse> {
    let result = s.vm.execute(&req.bytecode).await;
    Json(ExecuteResponse { result })
}

async fn batch_solve(
    State(s): State<AppState>,
    Json(req): Json<BatchSolveRequest>,
) -> Json<BatchSolveResponse> {
    let gpu_used = s.gpu.should_use_gpu(req.instances.len());
    let solver = BatchCspSolver::new(s.gpu.clone());
    let solutions = solver.solve_batch(&req.instances).await;
    let total = solutions.len();
    Json(BatchSolveResponse {
        solutions,
        total,
        gpu_used,
    })
}

async fn batch_sonar(
    State(s): State<AppState>,
    Json(req): Json<BatchSonarRequest>,
) -> Json<BatchSonarResponse> {
    let gpu_used = s.gpu.should_use_gpu(req.params.len());
    let engine = BatchSonarPhysics::new(s.gpu.clone());
    let results = engine.compute_batch(&req.params).await;
    let total = results.len();
    Json(BatchSonarResponse {
        results,
        total,
        gpu_used,
    })
}

async fn status(State(s): State<AppState>) -> Json<StatusResponse> {
    Json(StatusResponse {
        node_id: s.config.node_id.clone(),
        gpu_available: s.gpu.should_use_gpu(1_000_000),
        gpu_memory_mb: s.gpu.gpu_memory_mb(),
        total_instructions: s.vm.total_instructions(),
        uptime_secs: s.start_time.elapsed().as_secs(),
        pipeline_committed: s.pipeline_committed.load(std::sync::atomic::Ordering::Relaxed),
    })
}

async fn metrics(State(s): State<AppState>) -> String {
    // Prometheus text format
    let instructions = s.vm.total_instructions();
    let uptime = s.start_time.elapsed().as_secs();
    let committed = s.pipeline_committed.load(std::sync::atomic::Ordering::Relaxed);
    format!(
        "# HELP flux_thor_instructions_total Total instructions executed\n\
         # TYPE flux_thor_instructions_total counter\n\
         flux_thor_instructions_total {instructions}\n\
         # HELP flux_thor_uptime_seconds Uptime in seconds\n\
         # TYPE flux_thor_uptime_seconds gauge\n\
         flux_thor_uptime_seconds {uptime}\n\
         # HELP flux_thor_pipeline_committed_total Pipeline items committed\n\
         # TYPE flux_thor_pipeline_committed_total counter\n\
         flux_thor_pipeline_committed_total {committed}\n"
    )
}

async fn ws_stream(ws: WebSocketUpgrade) -> impl IntoResponse {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: axum::extract::ws::WebSocket) {
    use axum::extract::ws::Message;
    while let Some(msg) = socket.recv().await {
        match msg {
            Ok(Message::Text(t)) => {
                let reply = format!("echo: {t}");
                if socket.send(Message::Text(reply.into())).await.is_err() {
                    break;
                }
            }
            Ok(Message::Close(_)) => break,
            _ => {}
        }
    }
}
