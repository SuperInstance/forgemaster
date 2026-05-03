use axum::Router;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing_subscriber::EnvFilter;

use flux_verify_api::api::routes::{self, AppState};
use flux_verify_api::config::Config;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("flux_verify_api=info".parse().unwrap()))
        .init();

    let config = Config::from_env();
    let addr = config.bind_addr();

    let state = Arc::new(Mutex::new(AppState::new(config)));

    let app = Router::new()
        .merge(routes::router())
        .with_state(state);

    tracing::info!("🔥 flux-verify-api v0.1.0 listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
