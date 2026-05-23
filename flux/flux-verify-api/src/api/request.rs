use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct VerifyRequest {
    pub claim: String,
    #[serde(default = "default_domain")]
    pub domain: String,
    #[serde(default = "default_rigor")]
    pub rigor: String,
}

fn default_domain() -> String {
    "generic".into()
}

fn default_rigor() -> String {
    "standard".into()
}
