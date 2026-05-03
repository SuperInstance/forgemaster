use std::sync::Arc;
use plato_engine::server;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "plato_engine=info,tower_http=info".into()),
        )
        .init();

    let port: u16 = std::env::var("PLATO_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8847);

    let state = Arc::new(server::AppState {
        engine: plato_engine::PlatoEngine::with_defaults(),
    });

    let router = server::build_router(state);

    let addr = std::net::SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("🔨 PLATO Engine forging on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, router).await.unwrap();
}
