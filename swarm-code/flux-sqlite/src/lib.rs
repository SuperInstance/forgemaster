//! flux_sqlite_store — SQLite Constraint History Store

use rusqlite::{params, Connection, Result as SqlResult};
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct CheckRecord {
    pub id: Option<i64>,
    pub agent_id: String,
    pub constraint_name: String,
    pub passed: bool,
    pub latency_us: f64,
    pub inputs_json: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ViolationRecord {
    pub id: Option<i64>,
    pub agent_id: String,
    pub constraint_name: String,
    pub severity: String,
    pub observed_json: String,
    pub threshold_json: String,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HourlyAggregate {
    pub hour: String,
    pub agent_id: String,
    pub constraint_name: String,
    pub checks: i64,
    pub violations: i64,
}

pub struct ConstraintStore {
    conn: Connection,
}

impl ConstraintStore {
    pub fn open<P: AsRef<Path>>(path: P) -> SqlResult<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "PRAGMA journal_mode=WAL;
             PRAGMA synchronous=NORMAL;
             CREATE TABLE IF NOT EXISTS checks (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 agent_id TEXT NOT NULL,
                 constraint_name TEXT NOT NULL,
                 passed INTEGER NOT NULL,
                 latency_us REAL NOT NULL,
                 inputs_json TEXT NOT NULL,
                 timestamp TEXT NOT NULL
             );
             CREATE TABLE IF NOT EXISTS violations (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 agent_id TEXT NOT NULL,
                 constraint_name TEXT NOT NULL,
                 severity TEXT NOT NULL,
                 observed_json TEXT NOT NULL,
                 threshold_json TEXT NOT NULL,
                 message TEXT NOT NULL,
                 timestamp TEXT NOT NULL
             );
             CREATE INDEX IF NOT EXISTS idx_checks_time ON checks(timestamp);
             CREATE INDEX IF NOT EXISTS idx_violations_time ON violations(timestamp);
             CREATE INDEX IF NOT EXISTS idx_violations_name ON violations(constraint_name);
            "
        )?;
        Ok(ConstraintStore { conn })
    }

    pub fn record_check(&self, rec: &CheckRecord) -> SqlResult<()> {
        self.conn.execute(
            "INSERT INTO checks (agent_id, constraint_name, passed, latency_us, inputs_json, timestamp)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![&rec.agent_id, &rec.constraint_name, rec.passed as i32, rec.latency_us, &rec.inputs_json, rec.timestamp.to_rfc3339()],
        )?;
        Ok(())
    }

    pub fn record_violation(&self, rec: &ViolationRecord) -> SqlResult<()> {
        self.conn.execute(
            "INSERT INTO violations (agent_id, constraint_name, severity, observed_json, threshold_json, message, timestamp)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![&rec.agent_id, &rec.constraint_name, &rec.severity, &rec.observed_json, &rec.threshold_json, &rec.message, rec.timestamp.to_rfc3339()],
        )?;
        Ok(())
    }

    pub fn query_violations(&self, since: DateTime<Utc>, until: DateTime<Utc>, limit: usize) -> SqlResult<Vec<ViolationRecord>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, agent_id, constraint_name, severity, observed_json, threshold_json, message, timestamp
             FROM violations WHERE timestamp >= ?1 AND timestamp <= ?2 ORDER BY timestamp DESC LIMIT ?3"
        )?;
        let rows = stmt.query_map(params![since.to_rfc3339(), until.to_rfc3339(), limit as i64], |row| {
            let ts: String = row.get(7)?;
            Ok(ViolationRecord {
                id: row.get(0)?, agent_id: row.get(1)?, constraint_name: row.get(2)?,
                severity: row.get(3)?, observed_json: row.get(4)?, threshold_json: row.get(5)?,
                message: row.get(6)?,
                timestamp: DateTime::parse_from_rfc3339(&ts).map(|d| d.with_timezone(&Utc)).unwrap_or_else(|_| Utc::now()),
            })
        })?;
        rows.collect()
    }

    pub fn count_violations_since(&self, since: DateTime<Utc>) -> SqlResult<i64> {
        self.conn.query_row(
            "SELECT COUNT(*) FROM violations WHERE timestamp >= ?1",
            [since.to_rfc3339()], |row| row.get(0),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn in_memory_store() -> ConstraintStore {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(
            "CREATE TABLE checks (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, constraint_name TEXT NOT NULL, passed INTEGER NOT NULL, latency_us REAL NOT NULL, inputs_json TEXT NOT NULL, timestamp TEXT NOT NULL);
             CREATE TABLE violations (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, constraint_name TEXT NOT NULL, severity TEXT NOT NULL, observed_json TEXT NOT NULL, threshold_json TEXT NOT NULL, message TEXT NOT NULL, timestamp TEXT NOT NULL);"
        ).unwrap();
        ConstraintStore { conn }
    }

    #[test]
    fn test_record_and_query_violation() {
        let store = in_memory_store();
        store.record_violation(&ViolationRecord {
            id: None, agent_id: "a1".into(), constraint_name: "temp".into(),
            severity: "critical".into(), observed_json: r#"{"t":150}"#.into(),
            threshold_json: r#"{"max":120}"#.into(), message: "Overheat".into(), timestamp: Utc::now(),
        }).unwrap();
        let results = store.query_violations(Utc::now() - Duration::from_secs(60), Utc::now() + Duration::from_secs(60), 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].constraint_name, "temp");
    }

    #[test]
    fn test_record_check() {
        let store = in_memory_store();
        store.record_check(&CheckRecord {
            id: None, agent_id: "a1".into(), constraint_name: "rpm".into(),
            passed: true, latency_us: 12.5, inputs_json: r#"{"rpm":3000}"#.into(), timestamp: Utc::now(),
        }).unwrap();
    }

    #[test]
    fn test_count_violations_since() {
        let store = in_memory_store();
        store.record_violation(&ViolationRecord {
            id: None, agent_id: "a1".into(), constraint_name: "x".into(),
            severity: "warning".into(), observed_json: "{}".into(),
            threshold_json: "{}".into(), message: "".into(), timestamp: Utc::now(),
        }).unwrap();
        let count = store.count_violations_since(Utc::now() - Duration::from_secs(3600)).unwrap();
        assert_eq!(count, 1);
    }
}
