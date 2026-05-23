use snapkit_rs::Snapshot;
use std::collections::BTreeMap;

fn map(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
    pairs
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
}

#[test]
fn capture_creates_snapshot() {
    let snap = Snapshot::capture("initial", map(&[("x", "1"), ("y", "2")]));
    assert_eq!(snap.label, "initial");
    assert_eq!(snap.data.get("x").unwrap(), "1");
}

#[test]
fn diff_detects_no_changes() {
    let a = Snapshot::capture("a", map(&[("x", "1")]));
    let b = Snapshot::capture("b", map(&[("x", "1")]));
    assert!(a.diff(&b).is_empty());
}

#[test]
fn diff_detects_added_removed_changed() {
    let a = Snapshot::capture("v1", map(&[("x", "1"), ("y", "2")]));
    let b = Snapshot::capture("v2", map(&[("x", "99"), ("z", "3")]));

    let d = a.diff(&b);
    assert_eq!(d.added, vec!["z".to_string()]);
    assert_eq!(d.removed, vec!["y".to_string()]);
    assert_eq!(d.changed.len(), 1);
    assert_eq!(d.changed[0].key, "x");
    assert_eq!(d.changed[0].from, "1");
    assert_eq!(d.changed[0].to, "99");
}

#[test]
fn restore_merges_snapshots() {
    let base = Snapshot::capture("base", map(&[("x", "1"), ("y", "2")]));
    let patch = Snapshot::capture("patch", map(&[("y", "99"), ("z", "3")]));

    let restored = base.restore(&patch);
    assert_eq!(restored.data.get("x").unwrap(), "1"); // kept
    assert_eq!(restored.data.get("y").unwrap(), "99"); // patched
    assert_eq!(restored.data.get("z").unwrap(), "3"); // added
    assert_eq!(restored.label, "base+patch");
}
