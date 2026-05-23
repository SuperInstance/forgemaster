package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHealthz(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rr := httptest.NewRecorder()
	healthzHandler(rr, req)
	if rr.Code != http.StatusOK { t.Fatalf("expected 200, got %d", rr.Code) }
	if strings.TrimSpace(rr.Body.String()) != "ok" { t.Fatalf("unexpected body: %s", rr.Body.String()) }
}

func TestRecordBadMethod(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/record", nil)
	rr := httptest.NewRecorder()
	recordHandler(rr, req)
	if rr.Code != http.StatusMethodNotAllowed { t.Fatalf("expected 405, got %d", rr.Code) }
}

func TestRecordBadJSON(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/record", strings.NewReader("not json"))
	rr := httptest.NewRecorder()
	recordHandler(rr, req)
	if rr.Code != http.StatusBadRequest { t.Fatalf("expected 400, got %d", rr.Code) }
}

func TestRecordAndMetrics(t *testing.T) {
	payload := RecordPayload{AgentID: "test", ConstraintName: "c1", Checks: 100, Violations: 3, LatencyMicros: 12.5}
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/record", bytes.NewReader(body))
	rr := httptest.NewRecorder()
	recordHandler(rr, req)
	if rr.Code != http.StatusAccepted { t.Fatalf("expected 202, got %d", rr.Code) }
}
