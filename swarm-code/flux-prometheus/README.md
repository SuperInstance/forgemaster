# Prometheus Metrics Exporter

Go service exposing FLUX constraint metrics on `/metrics` (Prometheus format).

## Endpoints

- `GET /metrics` — Prometheus text format
- `POST /record` — Accept JSON payload, update internal metrics
- `GET /healthz` — Liveness probe

## Build & Run

```bash
cd flux-prometheus/
go mod tidy
go run flux_prometheus_exporter.go
# Visit http://localhost:9100/metrics
```

## Test

```bash
go test -v
```

## Requirements

- Go 1.22+
- `github.com/prometheus/client_golang`
