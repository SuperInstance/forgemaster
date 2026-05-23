use axum::Router;
use std::sync::Arc;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;

use flux_provenance::api::routes;
use flux_provenance::config::Config;
use flux_provenance::store::ProvenanceStore;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("info".parse().unwrap()))
        .init();

    let config = Config::from_env();
    tracing::info!("opening db at {}", config.db_path);
    let db = sled::open(&config.db_path).expect("failed to open sled db");
    let store = ProvenanceStore::new(db, config.batch_size);
    let state = routes::AppState {
        store: Arc::new(store),
    };

    let app = Router::new()
        .merge(routes::router(state))
        .layer(CorsLayer::permissive());

    let listener = tokio::net::TcpListener::bind(&config.listen_addr)
        .await
        .expect("failed to bind");
    tracing::info!("flux-provenance listening on {}", config.listen_addr);
    axum::serve(listener, app).await.expect("server error");
}
