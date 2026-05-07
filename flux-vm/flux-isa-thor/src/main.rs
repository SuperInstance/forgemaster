use std::sync::Arc;
use tracing::{error, info, warn};

use flux_isa_thor::config::ThorConfig;
use flux_isa_thor::cuda::GpuDispatcher;
use flux_isa_thor::fleet::{FleetHandle, FleetNode, NodeRole, NodeStatus};
use flux_isa_thor::plato::{PlatoHandle, cache::TileCache, client::PlatoClient};
use flux_isa_thor::server::{self, AppState};
use flux_isa_thor::vm::{ThorVm, VmConfig};
use flux_isa_thor::pipeline::{Pipeline, PipelineConfig};

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "flux_isa_thor=info".into()),
        )
        .init();

    info!("⚒️  FLUX ISA Thor — starting up");

    // ── Load configuration ───────────────────────────────────────
    let mut config = ThorConfig::default();
    config.apply_env();

    // Try loading from config file
    let config_path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "thor.toml".into());
    if std::path::Path::new(&config_path).exists() {
        match ThorConfig::load_from_file(std::path::Path::new(&config_path)) {
            Ok(file_config) => {
                let mut merged = file_config;
                merged.apply_env(); // env overrides file
                config = merged;
            }
            Err(e) => error!("Failed to load config from {config_path}: {e}"),
        }
    }

    info!("Node ID: {}", config.node_id);
    info!("Listen: {}", config.listen_addr);
    info!("PLATO: {}", config.plato_url);
    info!("GPU: {} ({}MB)", config.gpu_available, config.gpu_memory_mb);

    // ── Initialize GPU dispatcher ────────────────────────────────
    let gpu = Arc::new(GpuDispatcher::new(
        config.gpu_available,
        config.gpu_memory_mb,
        config.max_concurrent_kernels,
    ));
    info!(
        "GPU dispatcher ready — {} kernels, {} slots",
        config.max_concurrent_kernels,
        gpu.available_slots()
    );

    // ── Connect to PLATO ─────────────────────────────────────────
    let plato_client = Arc::new(PlatoClient::new(
        &config.plato_url,
        config.plato_max_concurrent,
        std::time::Duration::from_secs(30),
    ));
    let tile_cache = Arc::new(tokio::sync::RwLock::new(TileCache::new(config.cache_max_entries)));
    let plato = Arc::new(PlatoHandle::new(plato_client.clone(), tile_cache));

    match plato_client.health().await {
        Ok(true) => info!("PLATO connection healthy"),
        Ok(false) => warn!("PLATO health check returned false — running in degraded mode"),
        Err(e) => warn!("PLATO unreachable: {e} — running offline"),
    }

    // ── Initialize fleet ─────────────────────────────────────────
    let fleet_node = FleetNode {
        id: config.node_id.clone(),
        hostname: hostname::get()
            .map(|h| h.to_string_lossy().to_string())
            .unwrap_or_default(),
        role: NodeRole::Thor,
        gpu_available: config.gpu_available,
        gpu_memory_mb: config.gpu_memory_mb,
        status: NodeStatus::Online,
        last_heartbeat: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    };
    let fleet = Arc::new(FleetHandle::new(fleet_node));

    // Discover fleet peers
    for peer_url in &config.fleet_peers {
        info!("Fleet peer: {peer_url}");
        // Production: HTTP/gRPC discovery
    }

    // ── Initialize VM ────────────────────────────────────────────
    let vm_config = VmConfig {
        max_stack: config.vm_max_stack,
        ..VmConfig::default()
    };
    let vm = Arc::new(ThorVm::new(vm_config, gpu.clone(), plato.clone(), fleet.clone()));

    // ── GPU warmup ───────────────────────────────────────────────
    if config.gpu_available {
        info!("Warming up GPU — pre-compiling CUDA kernels...");
        // Production: trigger CUDA kernel JIT compilation
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        info!("GPU warmup complete");
    }

    // ── Start pipeline ───────────────────────────────────────────
    let pipeline_config = PipelineConfig {
        channel_capacity: config.pipeline_channel_capacity,
        max_concurrent_execute: config.pipeline_max_concurrent_execute,
        checkpoint_interval_secs: config.checkpoint_interval_secs,
        batch_size: config.pipeline_batch_size,
    };
    let pipeline = Arc::new(Pipeline::new(pipeline_config));
    let (tx_input, rx_input) = tokio::sync::mpsc::channel(1024);
    pipeline.run(rx_input).await;
    info!("Pipeline started — 5 stages");

    // ── Build shared state ───────────────────────────────────────
    let pipeline_committed = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let state = AppState {
        config: Arc::new(config.clone()),
        vm,
        gpu,
        plato,
        fleet,
        start_time: std::time::Instant::now(),
        pipeline_committed,
    };

    // ── Start HTTP server ────────────────────────────────────────
    let app = server::router(state);
    let listener = tokio::net::TcpListener::bind(config.listen_addr)
        .await
        .expect("failed to bind");
    info!("⚒️  FLUX ISA Thor listening on {}", config.listen_addr);

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("server error");

    info!("⚒️  FLUX ISA Thor — shutdown complete");
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c()
        .await
        .expect("failed to install Ctrl+C handler");
    info!("Received shutdown signal");
}
