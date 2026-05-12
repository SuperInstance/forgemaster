use crate::signing::{self, Signature, SigningError};
use std::collections::HashSet;
use tracing::{error, info, warn};

/// Middleware that verifies bytecode signatures before allowing execution.
pub struct VerificationMiddleware {
    /// Set of trusted Ed25519 public keys (32 bytes each).
    trusted_keys: HashSet<[u8; 32]>,
    /// If true, reject all unsigned bytecode. If false, log a warning but allow.
    strict: bool,
}

/// Result of a verification attempt.
#[derive(Debug)]
pub struct VerificationResult {
    pub allowed: bool,
    pub reason: String,
    pub key_index: Option<usize>,
}

impl VerificationMiddleware {
    /// Create a new middleware with at least one trusted public key.
    pub fn new(trusted_keys: Vec<[u8; 32]>) -> Self {
        assert!(
            !trusted_keys.is_empty(),
            "at least one trusted key required"
        );
        Self {
            trusted_keys: trusted_keys.into_iter().collect(),
            strict: true,
        }
    }

    /// Toggle strict mode. When strict (default), unsigned bytecode is rejected.
    pub fn with_strict(mut self, strict: bool) -> Self {
        self.strict = strict;
        self
    }

    /// Add a new trusted public key (for key rotation).
    pub fn add_trusted_key(&mut self, public_key: [u8; 32]) {
        info!("adding trusted public key: {:?}", hex::encode(public_key));
        self.trusted_keys.insert(public_key);
    }

    /// Remove a trusted public key (e.g., revoke a compromised key).
    pub fn remove_trusted_key(&mut self, public_key: &[u8; 32]) {
        info!("removing trusted public key: {:?}", hex::encode(public_key));
        self.trusted_keys.remove(public_key);
    }

    /// Number of currently trusted keys.
    pub fn trusted_key_count(&self) -> usize {
        self.trusted_keys.len()
    }

    /// Verify bytecode against all trusted public keys.
    ///
    /// Returns `Ok(VerificationResult)` if any trusted key validates the signature.
    /// Returns an error result if none match or if the bytecode is tampered.
    pub fn verify(&self, bytecode: &[u8], signature: &Signature) -> VerificationResult {
        let fingerprint_hex = hex::encode(signature.fingerprint);
        info!(
            fingerprint = %fingerprint_hex,
            timestamp = signature.timestamp,
            bytecode_len = bytecode.len(),
            "verification attempt started"
        );

        // Try each trusted key.
        for (idx, pk) in self.trusted_keys.iter().enumerate() {
            match signing::verify_bytecode(bytecode, signature, pk) {
                Ok(()) => {
                    info!(
                        fingerprint = %fingerprint_hex,
                        key_index = idx,
                        "bytecode signature verified"
                    );
                    return VerificationResult {
                        allowed: true,
                        reason: "signature verified".into(),
                        key_index: Some(idx),
                    };
                }
                Err(SigningError::FingerprintMismatch) => {
                    error!(
                        fingerprint = %fingerprint_hex,
                        "fingerprint mismatch — bytecode was tampered with"
                    );
                    return VerificationResult {
                        allowed: false,
                        reason: "fingerprint mismatch: bytecode was tampered with".into(),
                        key_index: None,
                    };
                }
                Err(SigningError::VerificationFailed) => {
                    // This key didn't match; try the next one.
                    continue;
                }
                Err(e) => {
                    warn!(error = %e, "verification error");
                    continue;
                }
            }
        }

        warn!(
            fingerprint = %fingerprint_hex,
            "no trusted key matched the signature"
        );
        VerificationResult {
            allowed: false,
            reason: "no trusted key matched the signature".into(),
            key_index: None,
        }
    }

    /// Verify bytecode or return an error message suitable for API responses.
    pub fn verify_or_reject(
        &self,
        bytecode: &[u8],
        signature: &Signature,
    ) -> Result<usize, String> {
        let result = self.verify(bytecode, signature);
        if result.allowed {
            Ok(result.key_index.unwrap())
        } else {
            Err(result.reason)
        }
    }

    /// Check whether unsigned bytecode should be allowed (depends on strict mode).
    pub fn allow_unsigned(&self) -> bool {
        if self.strict {
            warn!("unsigned bytecode rejected (strict mode)");
            false
        } else {
            warn!("unsigned bytecode allowed (non-strict mode — not recommended for production)");
            true
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::SigningKey;

    fn random_keypair() -> ([u8; 32], [u8; 32]) {
        let signing_key = SigningKey::generate(&mut rand::rngs::OsRng);
        let pk = signing_key.verifying_key().to_bytes();
        let sk = signing_key.to_bytes();
        (sk, pk)
    }

    #[test]
    fn verify_with_trusted_key() {
        let (sk, pk) = random_keypair();
        let mw = VerificationMiddleware::new(vec![pk]);
        let bytecode = b"LOAD x 42.0;";
        let sig = signing::sign_bytecode(bytecode, &sk, Some(9999));
        let result = mw.verify(bytecode, &sig);
        assert!(result.allowed);
    }

    #[test]
    fn reject_untrusted_key() {
        let (sk, _) = random_keypair();
        let (_, untrusted_pk) = random_keypair();
        let mw = VerificationMiddleware::new(vec![untrusted_pk]);
        let bytecode = b"LOAD x 42.0;";
        let sig = signing::sign_bytecode(bytecode, &sk, Some(9999));
        let result = mw.verify(bytecode, &sig);
        assert!(!result.allowed);
    }

    #[test]
    fn key_rotation_old_key_still_works() {
        let (sk_old, pk_old) = random_keypair();
        let (_sk_new, pk_new) = random_keypair();
        let mut mw = VerificationMiddleware::new(vec![pk_old]);
        mw.add_trusted_key(pk_new);
        assert_eq!(mw.trusted_key_count(), 2);

        // Old key signature should still verify.
        let bytecode = b"LOAD x 42.0;";
        let sig = signing::sign_bytecode(bytecode, &sk_old, Some(9999));
        let result = mw.verify(bytecode, &sig);
        assert!(result.allowed);
    }

    #[test]
    fn strict_mode_rejects_unsigned() {
        let (_, pk) = random_keypair();
        let mw = VerificationMiddleware::new(vec![pk]).with_strict(true);
        assert!(!mw.allow_unsigned());
    }

    #[test]
    fn non_strict_mode_allows_unsigned() {
        let (_, pk) = random_keypair();
        let mw = VerificationMiddleware::new(vec![pk]).with_strict(false);
        assert!(mw.allow_unsigned());
    }
}
