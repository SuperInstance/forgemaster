use reqwest::Client;
use serde_json::json;

/// PLATO client for submitting verification tiles.
#[derive(Debug, Clone)]
pub struct PlatoClient {
    base_url: String,
    token: Option<String>,
    client: Client,
}

impl PlatoClient {
    pub fn new(base_url: String, token: Option<String>) -> Self {
        Self {
            base_url,
            token,
            client: Client::new(),
        }
    }

    /// Submit a verification result to PLATO.
    pub async fn submit(
        &self,
        proof_hash: &str,
        verdict: &str,
        claim: &str,
    ) -> Result<String, String> {
        let url = format!("{}/tiles/submit", self.base_url);

        let body = json!({
            "proof_hash": proof_hash,
            "verdict": verdict,
            "claim": claim,
        });

        let mut req = self.client.post(&url).json(&body);
        if let Some(ref token) = self.token {
            req = req.bearer_auth(token);
        }

        let resp = req
            .send()
            .await
            .map_err(|e| format!("PLATO request failed: {}", e))?;

        if resp.status().is_success() {
            Ok(format!("submitted-{}", proof_hash.len()))
        } else {
            Err(format!("PLATO returned status {}", resp.status()))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plato_client_construction() {
        let client = PlatoClient::new("http://localhost:9999".into(), Some("test-token".into()));
        assert_eq!(client.base_url, "http://localhost:9999");
        assert_eq!(client.token, Some("test-token".into()));
    }

    #[test]
    fn test_plato_client_no_token() {
        let client = PlatoClient::new("http://localhost:9999".into(), None);
        assert!(client.token.is_none());
    }
}
