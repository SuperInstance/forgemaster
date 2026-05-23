use std::sync::Arc;
use std::time::Duration;

use flux_isa_edge::config::Config;
use flux_isa_edge::plato::client::{PlatoClient, PlatoConfig};
use flux_isa_edge::plato::sync::{PlatoCache, SyncConfig, start_background_sync};
use flux_isa_edge::sensor::pipeline::{Pipeline, PipelineConfig, ViolationPolicy};
use flux_isa_edge::sensor::sonar::SonarSensor;
use flux_isa_edge::server::{self, AppState};
use flux_isa_edge::vm::ExecutionLimits;

use tokio::sync::mpsc;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    // ── Logging ────────────────────────────────────
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("flux_isa_edge=info".parse().unwrap()))
        .init();

    // ── Config ─────────────────────────────────────
    let config = Config::load();
    tracing::info!(node_id = %config.node_id, "starting flux-isa-edge");

    // ── Execution limits ───────────────────────────
    let vm_limits = ExecutionLimits {
        max_steps: config.max_steps,
        max_time: Duration::from_secs_f64(config.max_time_secs),
        max_stack_depth: config.max_stack_depth,
    };

    // ── PLATO connection ───────────────────────────
    let plato_config = PlatoConfig {
        url: config.plato_url.clone(),
        ..Default::default()
    };

    let plato_client = match PlatoClient::connect(plato_config.clone()).await {
        Ok(client) => {
            tracing::info!(url = %config.plato_url, "connected to PLATO");
            client
        }
        Err(e) => {
            tracing::warn!(error = %e, "PLATO unreachable, starting in offline mode");
            PlatoClient::new_unchecked(plato_config)
        }
    };

    // ── PLATO cache & sync ─────────────────────────
    let cache = Arc::new(PlatoCache::new());
    let sync_config = SyncConfig {
        rooms: vec!["forgemaster".into(), "fleet-ops".into()],
        sync_interval: Duration::from_secs(config.sync_interval_secs),
        offline_mode: false,
    };
    let _sync_handle = start_background_sync(plato_client, cache.clone(), sync_config);

    // ── Sensor pipelines ───────────────────────────
    let (result_tx, mut result_rx) = mpsc::channel::<flux_isa_edge::sensor::pipeline::PipelineResult>(256);
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // Sonar pipeline.
    let sonar = SonarSensor::simulated(Default::default());
    let sonar_bytecode = sonar.validation_bytecode().clone();
    let pipeline_config = PipelineConfig {
        batch_size: config.batch_size,
        violation_policy: match config.violation_policy.as_str() {
            "halt" => ViolationPolicy::Halt,
            _ => ViolationPolicy::LogAndContinue,
        },
        ..Default::default()
    };

    let pipeline_shutdown = shutdown_rx.clone();
    let pipeline_limits = vm_limits.clone();
    tokio::spawn(async move {
        let pipeline = Pipeline::new(sonar, sonar_bytecode, pipeline_config, pipeline_limits);
        pipeline.run(result_tx, pipeline_shutdown).await;
    });

    // Pipeline result logger.
    let mut result_shutdown = shutdown_rx.clone();
    tokio::spawn(async move {
        loop {
            tokio::select! {
                result = result_rx.recv() => {
                    match result {
                        Some(r) => {
                            if r.passed {
                                tracing::debug!(sensor = %r.sensor_name, batch = %r.batch_id, "batch passed");
                            } else {
                                tracing::warn!(sensor = %r.sensor_name, batch = %r.batch_id, violations = r.execution.violations, "batch violations");
                            }
                        }
                        None => break,
                    }
                }
                _ = result_shutdown.changed() => break,
            }
        }
    });

    // ── HTTP server ────────────────────────────────
    let state = AppState {
        start_time: std::time::Instant::now(),
        tiles_processed: Arc::new(tokio::sync::RwLock::new(0)),
        constraint_violations: Arc::new(tokio::sync::RwLock::new(0)),
        vm_limits: vm_limits.clone(),
        node_id: config.node_id.clone(),
    };

    let app = server::build_router(state);
    let addr = format!("{}:{}", config.bind_addr, config.port);
    let listener = tokio::net::TcpListener::bind(&addr).await.expect("failed to bind");
    tracing::info!(%addr, "HTTP server listening");

    // ── Graceful shutdown ──────────────────────────
    let server_shutdown = shutdown_rx.clone();
    tokio::spawn(async move {
        tokio::signal::ctrl_c().await.expect("ctrl_c listener");
        tracing::info!("received SIGINT, shutting down");
        let _ = shutdown_tx.send(true);
    });

    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let mut rx = server_shutdown;
            let _ = rx.changed().await;
        })
        .await
        .expect("server error");

    tracing::info!("flux-isa-edge stopped");
}
