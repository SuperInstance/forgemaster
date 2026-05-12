use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// MQTT v5 transport using rumqtt.
/// For IoT sensors, cloud relay, publish-subscribe patterns.
pub struct MqttTransport {
    client: Option<rumqttc::AsyncClient>,
    eventloop: Option<rumqttc::EventLoop>,
    connected: bool,
    broker: String,
    topic: String,
}

impl MqttTransport {
    pub fn new(broker: impl Into<String>, topic: impl Into<String>) -> Self {
        Self {
            client: None,
            eventloop: None,
            connected: false,
            broker: broker.into(),
            topic: topic.into(),
        }
    }
}

#[async_trait::async_trait]
impl Transport for MqttTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        let mut mqttoptions = rumqttc::MqttOptions::new("flux-transport", &self.broker, 1883);
        mqttoptions.set_keep_alive(std::time::Duration::from_secs(5));
        
        let (client, eventloop) = rumqttc::AsyncClient::new(mqttoptions, 10);
        client.subscribe(&self.topic, rumqttc::QoS::AtLeastOnce).await
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;
        
        self.client = Some(client);
        self.eventloop = Some(eventloop);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let client = self.client.as_ref().ok_or(TransportError::NotConnected)?;
        let data = packet.to_bytes()?;
        client.publish(&self.topic, rumqttc::QoS::AtLeastOnce, false, data).await
            .map_err(|e| TransportError::SendFailed(e.to_string()))
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let el = self.eventloop.as_mut().ok_or(TransportError::NotConnected)?;
        loop {
            match el.poll().await {
                Ok(rumqttc::Event::Incoming(rumqttc::Incoming::Publish(publish))) => {
                    return FluxPacket::from_bytes(&publish.payload);
                }
                Ok(_) => continue,
                Err(e) => return Err(TransportError::RecvFailed(e.to_string())),
            }
        }
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        if let Some(client) = self.client.take() {
            let _ = client.disconnect().await;
        }
        self.eventloop = None;
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "mqtt",
            latency_us: Some(50_000), // ~50ms
            bandwidth_bps: Some(10_000_000),
            reliable: true,
            ordered: false,
            bidirectional: true,
            max_packet_size: Some(256 * 1024 * 1024), // MQTT 5.0
        }
    }
}
