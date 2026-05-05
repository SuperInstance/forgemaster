// flux_prometheus_exporter.go — Prometheus Metrics Exporter for FLUX
//
// Exposes constraint check counters, violation counters, latency histograms,
// and active constraint gauges on /metrics.
//
// Run: go run flux_prometheus_exporter.go
// Metrics: http://localhost:9100/metrics

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type RecordPayload struct {
	AgentID        string  `json:"agent_id"`
	ConstraintName string  `json:"constraint_name"`
	Checks         int64   `json:"checks"`
	Violations     int64   `json:"violations"`
	LatencyMicros  float64 `json:"latency_us"`
	UpdateRateHz   float64 `json:"update_rate_hz"`
}

var (
	checkCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "flux_constraint_checks_total",
			Help: "Total number of constraint checks performed.",
		},
		[]string{"agent_id", "constraint_name"},
	)
	violationCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "flux_constraint_violations_total",
			Help: "Total number of constraint violations detected.",
		},
		[]string{"agent_id", "constraint_name", "severity"},
	)
	latencyHistogram = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "flux_check_latency_microseconds",
			Help:    "Latency of constraint checks in microseconds.",
			Buckets: prometheus.ExponentialBuckets(1, 2, 16),
		},
		[]string{"agent_id", "constraint_name"},
	)
	activeGauge = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "flux_active_constraints",
			Help: "Number of currently active constraints per agent.",
		},
		[]string{"agent_id"},
	)
	violationRateGauge = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "flux_violation_rate_per_second",
			Help: "Current violation rate per second.",
		},
		[]string{"agent_id", "constraint_name"},
	)
)

func init() {
	prometheus.MustRegister(checkCounter)
	prometheus.MustRegister(violationCounter)
	prometheus.MustRegister(latencyHistogram)
	prometheus.MustRegister(activeGauge)
	prometheus.MustRegister(violationRateGauge)
}

type timePoint struct {
	ts  time.Time
	val float64
}

type rateAggregator struct {
	mu      sync.RWMutex
	windows map[string][]timePoint
}

var aggregator = &rateAggregator{windows: make(map[string][]timePoint)}

func (ra *rateAggregator) record(key string, violations float64) {
	ra.mu.Lock()
	defer ra.mu.Unlock()
	now := time.Now()
	ra.windows[key] = append(ra.windows[key], timePoint{ts: now, val: violations})
	cutoff := now.Add(-60 * time.Second)
	w := ra.windows[key]
	i := 0
	for i < len(w) && w[i].ts.Before(cutoff) { i++ }
	ra.windows[key] = w[i:]
}

func (ra *rateAggregator) ratePerSecond(key string) float64 {
	ra.mu.RLock()
	defer ra.mu.RUnlock()
	w := ra.windows[key]
	if len(w) < 2 { return 0 }
	duration := w[len(w)-1].ts.Sub(w[0].ts).Seconds()
	if duration <= 0 { return 0 }
	total := 0.0
	for _, p := range w { total += p.val }
	return total / duration
}

func recordHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var p RecordPayload
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	labels := prometheus.Labels{"agent_id": p.AgentID, "constraint_name": p.ConstraintName}
	checkCounter.With(labels).Add(float64(p.Checks))
	latencyHistogram.With(labels).Observe(p.LatencyMicros)

	if p.Violations > 0 {
		vlabels := prometheus.Labels{"agent_id": p.AgentID, "constraint_name": p.ConstraintName, "severity": "critical"}
		violationCounter.With(vlabels).Add(float64(p.Violations))
	}

	key := p.AgentID + "::" + p.ConstraintName
	aggregator.record(key, float64(p.Violations))
	violationRateGauge.With(labels).Set(aggregator.ratePerSecond(key))

	w.WriteHeader(http.StatusAccepted)
	fmt.Fprint(w, "ok\n")
}

func healthzHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "ok\n")
}

func main() {
	http.Handle("/metrics", promhttp.Handler())
	http.HandleFunc("/record", recordHandler)
	http.HandleFunc("/healthz", healthzHandler)

	addr := ":9100"
	log.Printf("FLUX Prometheus exporter listening on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}
