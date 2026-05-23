use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

/// Unique hash identifying a tile's content.
pub type TileHash = String;

/// Provenance metadata — who created this tile and how.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Provenance {
    pub agent_id: String,
    pub session_id: String,
    pub chain_hash: String,
    pub signature: String,
}

/// A PLATO knowledge tile — the fundamental unit of knowledge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tile {
    pub id: Uuid,
    pub domain: String,
    pub question: String,
    pub answer: String,
    pub source: String,
    pub confidence: f64,
    pub tags: Vec<String>,
    pub created_at: i64,
    pub provenance: Provenance,
}

impl Tile {
    /// Compute a content hash for deduplication.
    /// Hashes domain + question + answer + source (ignores metadata).
    pub fn content_hash(&self) -> TileHash {
        let mut hasher = Sha256::new();
        hasher.update(self.domain.as_bytes());
        hasher.update(self.question.as_bytes());
        hasher.update(self.answer.as_bytes());
        hasher.update(self.source.as_bytes());
        let result = hasher.finalize();
        hex::encode(result)
    }

    /// Validate that all required fields are present and non-empty.
    pub fn validate(&self) -> Result<(), TileValidationError> {
        if self.domain.trim().is_empty() {
            return Err(TileValidationError::EmptyField("domain".into()));
        }
        if self.question.trim().is_empty() {
            return Err(TileValidationError::EmptyField("question".into()));
        }
        if self.answer.trim().is_empty() {
            return Err(TileValidationError::EmptyField("answer".into()));
        }
        if self.source.trim().is_empty() {
            return Err(TileValidationError::EmptyField("source".into()));
        }
        if self.confidence < 0.0 || self.confidence > 1.0 {
            return Err(TileValidationError::InvalidConfidence(self.confidence));
        }
        if self.provenance.agent_id.trim().is_empty() {
            return Err(TileValidationError::EmptyField("provenance.agent_id".into()));
        }
        Ok(())
    }
}

#[derive(Debug, thiserror::Error)]
pub enum TileValidationError {
    #[error("empty field: {0}")]
    EmptyField(String),
    #[error("invalid confidence: {0} (must be 0.0-1.0)")]
    InvalidConfidence(f64),
}

/// Builder for constructing tiles with validation.
#[derive(Debug, Default)]
pub struct TileBuilder {
    domain: Option<String>,
    question: Option<String>,
    answer: Option<String>,
    source: Option<String>,
    confidence: Option<f64>,
    tags: Vec<String>,
    provenance: Option<Provenance>,
}

impl TileBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn domain(mut self, domain: impl Into<String>) -> Self {
        self.domain = Some(domain.into());
        self
    }

    pub fn question(mut self, question: impl Into<String>) -> Self {
        self.question = Some(question.into());
        self
    }

    pub fn answer(mut self, answer: impl Into<String>) -> Self {
        self.answer = Some(answer.into());
        self
    }

    pub fn source(mut self, source: impl Into<String>) -> Self {
        self.source = Some(source.into());
        self
    }

    pub fn confidence(mut self, confidence: f64) -> Self {
        self.confidence = Some(confidence);
        self
    }

    pub fn tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    pub fn tag(mut self, tag: impl Into<String>) -> Self {
        self.tags.push(tag.into());
        self
    }

    pub fn provenance(mut self, provenance: Provenance) -> Self {
        self.provenance = Some(provenance);
        self
    }

    pub fn build(self) -> Result<Tile, TileBuildError> {
        let domain = self.domain.ok_or(TileBuildError::MissingField("domain"))?;
        let question = self.question.ok_or(TileBuildError::MissingField("question"))?;
        let answer = self.answer.ok_or(TileBuildError::MissingField("answer"))?;
        let source = self.source.ok_or(TileBuildError::MissingField("source"))?;
        let confidence = self.confidence.ok_or(TileBuildError::MissingField("confidence"))?;
        let provenance = self.provenance.ok_or(TileBuildError::MissingField("provenance"))?;

        let tile = Tile {
            id: Uuid::new_v4(),
            domain,
            question,
            answer,
            source,
            confidence,
            tags: self.tags,
            created_at: chrono::Utc::now().timestamp(),
            provenance,
        };

        tile.validate().map_err(TileBuildError::Validation)?;

        Ok(tile)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum TileBuildError {
    #[error("missing required field: {0}")]
    MissingField(&'static str),
    #[error("validation failed: {0}")]
    Validation(#[from] TileValidationError),
}
