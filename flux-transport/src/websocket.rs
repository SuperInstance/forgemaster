use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};
use futures_util::{SinkExt, StreamExt};

/// WebSocket transport using tokio-tungstenite.
/// For browser dashboards, live monitoring, remote control.
pub struct WebSocketTransport {
    stream: Option<
        tokio_tungstenite::WebSocketStream<
            tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
        >,
    >,
    connected: bool,
    url: String,
}

impl WebSocketTransport {
    pub fn new(url: impl Into<String>) -> Self {
        Self {
            stream: None,
            connected: false,
            url: url.into(),
        }
    }
}

#[async_trait::async_trait]
impl Transport for WebSocketTransport {
    async fn connect(&mut self, config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        let settings = config
            .get("websocket")
            .map(|e| e.settings.clone())
            .unwrap_or_default();
        let url = settings.get("url").map(|s| s.as_str()).unwrap_or(&self.url);

        let (stream, _response) = tokio_tungstenite::connect_async(url)
            .await
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;

        self.stream = Some(stream);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.stream.as_mut() {
            Some(ws) => {
                use tokio_tungstenite::tungstenite::Message;
                let data = packet.to_bytes()?;
                ws.send(Message::Binary(data.into()))
                    .await
                    .map_err(|e| TransportError::SendFailed(e.to_string()))
            }
            None => Err(TransportError::NotConnected),
        }
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.stream.as_mut() {
            Some(ws) => {
                use tokio_tungstenite::tungstenite::Message;
                let msg = ws
                    .next()
                    .await
                    .ok_or(TransportError::RecvFailed("stream ended".into()))?
                    .map_err(|e| TransportError::RecvFailed(e.to_string()))?;
                match msg {
                    Message::Binary(data) => FluxPacket::from_bytes(&data),
                    Message::Text(text) => FluxPacket::from_bytes(text.as_bytes()),
                    _ => Err(TransportError::RecvFailed("unexpected message type".into())),
                }
            }
            None => Err(TransportError::NotConnected),
        }
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        if let Some(mut ws) = self.stream.take() {
            use tokio_tungstenite::tungstenite::protocol::frame::coding::CloseCode;
            let _ = ws
                .close(Some(tokio_tungstenite::tungstenite::protocol::CloseFrame {
                    code: CloseCode::Normal,
                    reason: std::borrow::Cow::Borrowed("disconnect"),
                }))
                .await;
        }
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "websocket",
            latency_us: Some(5_000),
            bandwidth_bps: Some(100_000_000),
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: None,
        }
    }
}
