//! Integration tests for FLUX bytecode signing and verification middleware.

use ed25519_dalek::SigningKey;

fn random_keypair() -> ([u8; 32], [u8; 32]) {
    let signing_key = SigningKey::generate(&mut rand::rngs::OsRng);
    let pk = signing_key.verifying_key().to_bytes();
    let sk = signing_key.to_bytes();
    (sk, pk)
}

/// Sign valid bytecode and verify it round-trips.
#[test]
fn sign_and_verify_valid_bytecode() {
    let (sk, pk) = random_keypair();
    let bytecode = br#"{"opcode":"LOAD","name":"x","value":42.0,"desc":"test"}"#;
    let sig = flux_verify_api::signing::sign_bytecode(bytecode, &sk, Some(1000));
    assert!(
        flux_verify_api::signing::verify_bytecode(bytecode, &sig, &pk).is_ok(),
        "valid signature should verify"
    );
}

/// Flip one byte in the bytecode after signing — must be rejected.
#[test]
fn reject_tampered_bytecode() {
    let (sk, pk) = random_keypair();
    let bytecode = br#"{"opcode":"LOAD","name":"x","value":42.0,"desc":"test"}"#;
    let sig = flux_verify_api::signing::sign_bytecode(bytecode, &sk, Some(1000));

    let mut tampered = bytecode.to_vec();
    tampered[10] ^= 0xFF;

    let result = flux_verify_api::signing::verify_bytecode(&tampered, &sig, &pk);
    assert!(result.is_err(), "tampered bytecode must be rejected");
}

/// Sign with one key, verify against a different key — must fail.
#[test]
fn reject_wrong_public_key() {
    let (sk, _pk) = random_keypair();
    let (_, wrong_pk) = random_keypair();
    let bytecode = b"LOAD x 1.0";
    let sig = flux_verify_api::signing::sign_bytecode(bytecode, &sk, Some(1000));

    let result = flux_verify_api::signing::verify_bytecode(bytecode, &sig, &wrong_pk);
    assert!(result.is_err(), "wrong public key must be rejected");
}

/// Key rotation: add a new key, old key signatures still validate.
#[test]
fn key_rotation_old_key_still_works() {
    let (sk_old, pk_old) = random_keypair();
    let (sk_new, pk_new) = random_keypair();

    let mut mw = flux_verify_api::verify_middleware::VerificationMiddleware::new(vec![pk_old]);

    // Sign with old key — should verify.
    let bytecode = b"GENERIC_COMPARE 5.0 > 3.0 test";
    let sig_old = flux_verify_api::signing::sign_bytecode(bytecode, &sk_old, Some(1000));
    let result = mw.verify(bytecode, &sig_old);
    assert!(result.allowed, "old key should still be trusted");

    // Rotate: add new key.
    mw.add_trusted_key(pk_new);

    // Old key signature should STILL work.
    let result2 = mw.verify(bytecode, &sig_old);
    assert!(result2.allowed, "old key must still work after rotation");

    // New key signature should also work.
    let sig_new = flux_verify_api::signing::sign_bytecode(bytecode, &sk_new, Some(2000));
    let result3 = mw.verify(bytecode, &sig_new);
    assert!(result3.allowed, "new key should verify after rotation");
}

/// After revoking the old key, old-key signatures are rejected.
#[test]
fn key_revocation() {
    let (sk_old, pk_old) = random_keypair();
    let (sk_new, pk_new) = random_keypair();

    let mut mw = flux_verify_api::verify_middleware::VerificationMiddleware::new(vec![pk_old, pk_new]);

    let bytecode = b"THERMAL_BOUND 85.0 0.0 100.0";
    let sig_old = flux_verify_api::signing::sign_bytecode(bytecode, &sk_old, Some(1000));
    assert!(mw.verify(bytecode, &sig_old).allowed);

    // Revoke old key.
    mw.remove_trusted_key(&pk_old);

    // Old key is now rejected.
    let result = mw.verify(bytecode, &sig_old);
    assert!(!result.allowed, "revoked key should be rejected");

    // New key still works.
    let sig_new = flux_verify_api::signing::sign_bytecode(bytecode, &sk_new, Some(2000));
    assert!(mw.verify(bytecode, &sig_new).allowed, "new key still trusted");
}
