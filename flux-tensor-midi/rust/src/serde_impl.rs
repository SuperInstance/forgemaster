/// Serde serialization support for FLUX-Tensor-MIDI types.
///
/// Only compiled when the `serde` feature is enabled.
///
/// ```toml
/// [dependencies]
/// flux-tensor-midi = { features = ["serde"] }
/// ```

// Core types
#[cfg(feature = "serde")]
impl serde::Serialize for crate::core::FluxChannel {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("FluxChannel", 2)?;
        s.serialize_field("intensity", &self.intensity)?;
        s.serialize_field("cluster", &self.cluster)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl<'de> serde::Deserialize<'de> for crate::core::FluxChannel {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(serde::Deserialize)]
        struct FluxChannelHelper {
            intensity: i8,
            cluster: Option<u8>,
        }
        let helper = FluxChannelHelper::deserialize(deserializer)?;
        Ok(crate::core::FluxChannel {
            intensity: helper.intensity,
            cluster: helper.cluster,
        })
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::core::FluxVector {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("FluxVector", 1)?;
        s.serialize_field("channels", &self.channels)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl<'de> serde::Deserialize<'de> for crate::core::FluxVector {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(serde::Deserialize)]
        struct FluxVectorHelper {
            channels: [crate::core::FluxChannel; 9],
        }
        let helper = FluxVectorHelper::deserialize(deserializer)?;
        Ok(crate::core::FluxVector::new(helper.channels))
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::core::TZeroClock {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("TZeroClock", 4)?;
        s.serialize_field("tick", &self.tick)?;
        s.serialize_field("ema", &self.ema)?;
        s.serialize_field("alpha", &self.alpha())?;
        s.serialize_field("n_ticks", &self.n_ticks)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl<'de> serde::Deserialize<'de> for crate::core::TZeroClock {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(serde::Deserialize)]
        struct TZeroClockHelper {
            tick: f64,
            ema: f64,
            alpha: f64,
            n_ticks: u64,
        }
        let helper = TZeroClockHelper::deserialize(deserializer)?;
        let mut clock = crate::core::TZeroClock::new(helper.alpha);
        clock.tick = helper.tick;
        clock.ema = helper.ema;
        clock.n_ticks = helper.n_ticks;
        Ok(clock)
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::midi::events::MidiEvent {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("MidiEvent", 5)?;
        s.serialize_field("status", &self.status)?;
        s.serialize_field("data1", &self.data1)?;
        s.serialize_field("data2", &self.data2)?;
        s.serialize_field("velocity", &self.velocity)?;
        s.serialize_field("timestamp", &self.timestamp)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::sidechannel::nod::Nod {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("Nod", 3)?;
        s.serialize_field("note", &self.note)?;
        s.serialize_field("intensity", &self.intensity)?;
        s.serialize_field("enthusiastic", &self.enthusiastic)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::sidechannel::smile::Smile {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("Smile", 3)?;
        s.serialize_field("source", &self.source)?;
        s.serialize_field("warmth", &self.warmth)?;
        s.serialize_field("broad", &self.broad)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::sidechannel::frown::Frown {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let mut s = serializer.serialize_struct("Frown", 3)?;
        s.serialize_field("note", &self.note)?;
        s.serialize_field("displeasure", &self.displeasure)?;
        s.serialize_field("strong", &self.strong)?;
        s.end()
    }
}

#[cfg(feature = "serde")]
impl serde::Serialize for crate::harmony::chord::ChordQuality {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(self.to_string().as_str())
    }
}
