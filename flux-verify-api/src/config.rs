use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub plato_url: Option<String>,
    pub plato_token: Option<String>,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            host: env::var("VERIFY_HOST").unwrap_or_else(|_| "0.0.0.0".into()),
            port: env::var("VERIFY_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8080),
            plato_url: env::var("VERIFY_PLATO_URL").ok(),
            plato_token: env::var("VERIFY_PLATO_TOKEN").ok(),
        }
    }

    pub fn bind_addr(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }
}
