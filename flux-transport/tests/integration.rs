use flux_transport::*;

#[tokio::test]
async fn test_flux_packet_roundtrip() {
    let packet = FluxPacket::new("room1", "room2", vec![1, 2, 3, 4])
        .with_correlation_id("test-123")
        .with_priority(1);
    
    let bytes = packet.to_bytes().unwrap();
    let decoded = FluxPacket::from_bytes(&bytes).unwrap();
    
    assert_eq!(decoded.source, "room1");
    assert_eq!(decoded.target, "room2");
    assert_eq!(decoded.payload, vec![1, 2, 3, 4]);
    assert_eq!(decoded.correlation_id, Some("test-123".to_string()));
    assert_eq!(decoded.priority, 1);
}

#[tokio::test]
async fn test_memory_transport_roundtrip() {
    let (mut tx, mut rx) = memory::MemoryTransport::pair(16);
    
    assert!(tx.is_connected());
    assert!(rx.is_connected());
    
    let packet = FluxPacket::new("source", "dest", b"hello flux".to_vec());
    tx.send(&packet).await.unwrap();
    
    let received = rx.recv().await.unwrap();
    assert_eq!(received.source, "source");
    assert_eq!(received.target, "dest");
    assert_eq!(received.payload, b"hello flux");
}

#[tokio::test]
async fn test_memory_transport_disconnect() {
    let (mut a, mut b) = memory::MemoryTransport::pair(16);
    a.disconnect().await.unwrap();
    assert!(!a.is_connected());
    // b is still connected
    assert!(b.is_connected());
}

#[tokio::test]
async fn test_file_transport_roundtrip() {
    let dir = std::env::temp_dir().join("flux_test_file_transport");
    let _ = std::fs::remove_dir_all(&dir);
    
    let config = TransportConfig::default();
    
    let mut writer = file::FileTransport::new(&dir);
    writer.connect(&config).await.unwrap();
    
    let packet = FluxPacket::new("writer", "reader", b"file data".to_vec());
    writer.send(&packet).await.unwrap();
    writer.disconnect().await.unwrap();
    
    let mut reader = file::FileTransport::new(&dir);
    reader.connect(&config).await.unwrap();
    
    let received = reader.recv().await.unwrap();
    assert_eq!(received.source, "writer");
    assert_eq!(received.payload, b"file data");
    
    let _ = std::fs::remove_dir_all(&dir);
}

#[tokio::test]
async fn test_transport_manager_routing() {
    let mut manager = manager::TransportManager::new();
    
    let (tx1, _) = memory::MemoryTransport::pair(16);
    let (tx2, _) = memory::MemoryTransport::pair(16);
    
    manager.register("sensor_bus", Box::new(tx1));
    manager.register("dashboard", Box::new(tx2));
    
    manager.add_route("sensor/*", "sensor_bus");
    manager.add_route("dashboard", "dashboard");
    manager.add_route("*", "dashboard"); // fallback
    
    // Verify health check
    let health = manager.health_check().await;
    assert_eq!(health.len(), 2);
}

#[tokio::test]
async fn test_transport_manager_discover() {
    let mut manager = manager::TransportManager::new();
    let discovered = manager.discover().await;
    // Memory transport should always be discovered
    assert!(discovered.iter().any(|m| m.name == "memory"));
}

#[tokio::test]
async fn test_transport_config() {
    let config = TransportConfig::default()
        .with(TransportEntry {
            name: "tcp_main".into(),
            kind: TransportKind::Tcp,
            enabled: true,
            settings: {
                let mut s = std::collections::HashMap::new();
                s.insert("addr".into(), "127.0.0.1:8080".into());
                s
            },
        })
        .with(TransportEntry {
            name: "serial_gps".into(),
            kind: TransportKind::Serial,
            enabled: true,
            settings: {
                let mut s = std::collections::HashMap::new();
                s.insert("port".into(), "/dev/ttyUSB0".into());
                s.insert("baud".into(), "115200".into());
                s
            },
        });
    
    assert_eq!(config.transports.len(), 2);
    assert_eq!(config.get("tcp_main").unwrap().kind, TransportKind::Tcp);
    assert_eq!(config.get("serial_gps").unwrap().settings.get("baud").unwrap(), "115200");
}

#[tokio::test]
async fn test_transport_metadata() {
    let (tx, _) = memory::MemoryTransport::pair(16);
    let meta = tx.metadata();
    assert_eq!(meta.name, "memory");
    assert_eq!(meta.latency_us, Some(0));
    assert!(meta.reliable);
    assert!(meta.bidirectional);
}

#[test]
fn test_transport_kind_name() {
    assert_eq!(TransportKind::Tcp.name(), "tcp");
    assert_eq!(TransportKind::WebSocket.name(), "websocket");
    assert_eq!(TransportKind::Mqtt.name(), "mqtt");
    assert_eq!(TransportKind::Memory.name(), "memory");
}

#[tokio::test]
async fn test_error_states() {
    let mut t = memory::MemoryTransport::new(16);
    assert!(!t.is_connected());
    
    // Send without connect should fail
    let packet = FluxPacket::new("a", "b", vec![]);
    let result = t.send(&packet).await;
    assert!(result.is_err());
    
    // Recv without connect should fail
    let result = t.recv().await;
    assert!(result.is_err());
}
