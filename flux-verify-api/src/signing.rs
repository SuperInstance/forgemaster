use ed25519_dalek::{SigningKey, VerifyingKey, Signer, Verifier, Signature as DalekSignature};
use sha2::{Sha256, Digest};
use serde::{Serialize, Deserialize};

/// A signed bytecode blob: Ed25519 signature + SHA-256 fingerprint + timestamp.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signature {
    /// 64-byte Ed25519 signature over (fingerprint || timestamp_le_bytes).
    pub sig: [u8; 64],
    /// SHA-256 hash of the bytecode.
    pub fingerprint: [u8; 32],
    /// Unix timestamp (seconds, little-endian) when the signature was created.
    pub timestamp: u32,
}

/// Errors produced by signing / verification.
#[derive(Debug, thiserror::Error)]
pub enum SigningError {
    #[error("invalid private key length: expected 32 bytes, got {0}")]
    InvalidPrivateKey(usize),
    #[error("invalid public key: {0}")]
    InvalidPublicKey(String),
    #[error("signature verification failed")]
    VerificationFailed,
    #[error("fingerprint mismatch — bytecode was tampered with")]
    FingerprintMismatch,
}

impl Signature {
    /// Return the message that gets signed: fingerprint || timestamp_le_bytes.
    fn signed_message(fingerprint: &[u8; 32], timestamp: u32) -> [u8; 36] {
        let mut msg = [0u8; 36];
        msg[..32].copy_from_slice(fingerprint);
        msg[32..].copy_from_slice(&timestamp.to_le_bytes());
        msg
    }
}

/// Compute SHA-256 fingerprint of arbitrary bytecode.
pub fn fingerprint(bytecode: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(bytecode);
    hasher.finalize().into()
}

/// Sign bytecode with an Ed25519 private key.
///
/// `private_key` must be exactly 32 bytes (seed material for `ed25519-dalek`).
/// The signature covers the SHA-256 fingerprint of the bytecode concatenated
/// with a 4-byte little-endian timestamp.
pub fn sign_bytecode(bytecode: &[u8], private_key: &[u8; 32], timestamp: Option<u32>) -> Signature {
    let signing_key = SigningKey::from_bytes(private_key);
    let fp = fingerprint(bytecode);
    let ts = timestamp.unwrap_or_else(|| {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock went backwards")
            .as_secs() as u32
    });
    let msg = Signature::signed_message(&fp, ts);
    let dalek_sig: DalekSignature = signing_key.sign(&msg);
    let sig_bytes: [u8; 64] = dalek_sig.to_bytes();

    Signature {
        sig: sig_bytes,
        fingerprint: fp,
        timestamp: ts,
    }
}

/// Verify a bytecode signature against a trusted Ed25519 public key.
///
/// Returns `Ok(())` on success, or an error describing why verification failed.
pub fn verify_bytecode(
    bytecode: &[u8],
    signature: &Signature,
    public_key: &[u8; 32],
) -> Result<(), SigningError> {
    // 1. Re-derive fingerprint and check it matches what was signed.
    let fp = fingerprint(bytecode);
    if fp != signature.fingerprint {
        return Err(SigningError::FingerprintMismatch);
    }

    // 2. Reconstruct the signed message.
    let msg = Signature::signed_message(&signature.fingerprint, signature.timestamp);

    // 3. Verify Ed25519 signature.
    let verifying_key = VerifyingKey::from_bytes(public_key)
        .map_err(|e| SigningError::InvalidPublicKey(e.to_string()))?;
    let dalek_sig = DalekSignature::from_bytes(&signature.sig);
    verifying_key
        .verify(&msg, &dalek_sig)
        .map_err(|_| SigningError::VerificationFailed)?;

    Ok(())
}

#[cfg(test)]
mod unit {
    use super::*;

    fn random_keypair() -> ([u8; 32], [u8; 32]) {
        let signing_key = SigningKey::generate(&mut rand::rngs::OsRng);
        let public_key = signing_key.verifying_key().to_bytes();
        let private_key = signing_key.to_bytes();
        (private_key, public_key)
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let (sk, pk) = random_keypair();
        let bytecode = b"LOAD x 42.0; ASSERT_GT x 0;";
        let sig = sign_bytecode(bytecode, &sk, Some(12345));
        assert!(verify_bytecode(bytecode, &sig, &pk).is_ok());
    }

    #[test]
    fn reject_tampered_bytecode() {
        let (sk, pk) = random_keypair();
        let bytecode = b"LOAD x 42.0; ASSERT_GT x 0;";
        let sig = sign_bytecode(bytecode, &sk, Some(12345));
        let mut tampered = bytecode.to_vec();
        tampered[5] ^= 0xFF; // flip a byte
        assert!(verify_bytecode(&tampered, &sig, &pk).is_err());
    }

    #[test]
    fn reject_wrong_public_key() {
        let (sk, _) = random_keypair();
        let (_, wrong_pk) = random_keypair();
        let bytecode = b"LOAD x 42.0;";
        let sig = sign_bytecode(bytecode, &sk, Some(12345));
        assert!(verify_bytecode(bytecode, &sig, &wrong_pk).is_err());
    }
}
