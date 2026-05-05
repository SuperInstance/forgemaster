# Dockerfile — Hardened FLUX Safety Container
# Stage 1: Build
FROM rust:1.78-alpine3.19 AS builder
WORKDIR /build
RUN apk add --no-cache musl-dev openssl-dev protobuf-dev

COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release --target x86_64-unknown-linux-musl

# Stage 2: Runtime (hardened)
FROM alpine:3.19.1 AS runtime
LABEL maintainer="flux-rd@example.com"
LABEL org.opencontainers.image.title="FLUX Safety Container"

RUN apk add --no-cache libgcc ca-certificates && \
    addgroup -g 65534 -S flux && \
    adduser -u 65534 -S flux -G flux && \
    mkdir -p /data /tmp /var/run && \
    chown -R flux:flux /data /tmp /var/run

COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/flux-safety /usr/local/bin/flux-safety
RUN chmod 755 /usr/local/bin/flux-safety && chown root:root /usr/local/bin/flux-safety

COPY flux-seccomp.json /etc/flux/seccomp.json

ENV RUST_LOG=info
ENV FLUX_DB_PATH=/data/constraints.db
ENV FLUX_CONFIG_PATH=/etc/flux/config.toml

EXPOSE 9100 50051

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /usr/local/bin/flux-safety --healthcheck || exit 1

USER flux:flux

VOLUME ["/data", "/tmp"]

ENTRYPOINT ["/usr/local/bin/flux-safety"]
CMD ["--config", "/etc/flux/config.toml"]
