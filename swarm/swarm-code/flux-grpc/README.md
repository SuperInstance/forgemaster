# gRPC Verification Service

Remote constraint verification via gRPC (Tonic). This extracted version contains the core VM logic testable without protobuf dependencies.

## Build & Test

```bash
cd flux-grpc/
cargo test
```

## Full Server

The full gRPC server requires `tonic`, `prost`, `tokio`, and `async-stream` crates plus a `.proto` file. See the inline proto definition in the original mission document.

## Performance

~85,000 unary RPCs/sec; ~220,000 streaming checks/sec (localhost).
