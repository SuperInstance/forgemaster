//! Streaming — real-time stream processing via iterators.
//!
//! No async dependencies. All streaming is iterator-based, zero-copy where
//! possible, and thread-safe. The stream processor maintains internal state
//! (a ring buffer of recent values) for delta-based processing.

use crate::snap::{SnapFunction, SnapResult};

/// A sliding window over a stream of values.
///
/// Maintains a fixed-size ring buffer of the most recent observations.
/// Efficient for real-time processing — O(1) insertion, no heap allocation
/// after construction.
#[derive(Debug, Clone)]
pub struct RingBuffer<T: Copy + Default> {
    buffer: Vec<T>,
    capacity: usize,
    head: usize,
    count: usize,
}

impl<T: Copy + Default> RingBuffer<T> {
    /// Create a new ring buffer with the given capacity.
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: vec![T::default(); capacity],
            capacity,
            head: 0,
            count: 0,
        }
    }

    /// Push a value into the buffer (O(1)).
    pub fn push(&mut self, value: T) {
        self.buffer[self.head] = value;
        self.head = (self.head + 1) % self.capacity;
        if self.count < self.capacity {
            self.count += 1;
        }
    }

    /// Get the most recent value, if any.
    pub fn last(&self) -> Option<T> {
        if self.count == 0 {
            return None;
        }
        let idx = if self.head == 0 {
            self.capacity - 1
        } else {
            self.head - 1
        };
        Some(self.buffer[idx])
    }

    /// Get all values in oldest-to-newest order.
    pub fn values(&self) -> Vec<T> {
        let mut result = Vec::with_capacity(self.count);
        if self.count == 0 {
            return result;
        }
        // Start from the oldest element
        let start = if self.count < self.capacity {
            0
        } else {
            self.head
        };
        for i in 0..self.count {
            let idx = (start + i) % self.capacity;
            result.push(self.buffer[idx]);
        }
        result
    }

    /// Number of elements currently in the buffer.
    pub fn len(&self) -> usize {
        self.count
    }

    /// Is the buffer empty?
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }

    /// Is the buffer full?
    pub fn is_full(&self) -> bool {
        self.count == self.capacity
    }

    /// Mean of current values.
    pub fn mean(&self) -> Option<f64>
    where
        T: Into<f64>,
    {
        if self.is_empty() {
            return None;
        }
        let sum: f64 = self.values().into_iter().map(|v| v.into()).sum();
        Some(sum / self.count as f64)
    }

    /// Standard deviation of current values.
    pub fn std_dev(&self) -> Option<f64>
    where
        T: Into<f64>,
    {
        let mean = self.mean()?;
        if self.count < 2 {
            return None;
        }
        let variance: f64 = self
            .values()
            .into_iter()
            .map(|v| {
                let d = v.into() - mean;
                d * d
            })
            .sum::<f64>()
            / (self.count - 1) as f64;
        Some(variance.sqrt())
    }
}

/// Configurable stream processor.
///
/// Processes a stream of values through a snap function, optionally
/// maintaining a sliding window and computing stream statistics.
///
/// # Examples
///
/// ```
/// use snapkit::{StreamProcessor, SnapFunction};
///
/// let snap = SnapFunction::<f64>::new();
/// let mut processor = StreamProcessor::new(snap).with_window(10);
///
/// for value in [0.05, 0.02, 0.3, 0.04, 0.08].iter() {
///     let result = processor.feed(*value);
///     // result.is_delta() tells us if value exceeded tolerance
/// }
///
/// assert_eq!(processor.count(), 5);
/// assert_eq!(processor.delta_count(), 1);
/// ```
#[derive(Debug, Clone)]
pub struct StreamProcessor {
    snap: SnapFunction<f64>,
    window: Option<RingBuffer<f64>>,
    count: u64,
    deltas: u64,
}

impl StreamProcessor {
    /// Create a new stream processor with the given snap function.
    pub fn new(snap: SnapFunction<f64>) -> Self {
        Self {
            snap,
            window: None,
            count: 0,
            deltas: 0,
        }
    }

    /// Enable sliding window tracking with the given capacity.
    pub fn with_window(mut self, capacity: usize) -> Self {
        self.window = Some(RingBuffer::new(capacity));
        self
    }

    /// Feed a value into the processor.
    ///
    /// Returns the snap result.
    pub fn feed(&mut self, value: f64) -> SnapResult<f64> {
        let result = self.snap.observe(value);
        self.count += 1;
        if result.is_delta() {
            self.deltas += 1;
        }
        if let Some(ref mut buf) = self.window {
            buf.push(value);
        }
        result
    }

    /// Get a reference to the underlying snap function.
    pub fn snap(&self) -> &SnapFunction<f64> {
        &self.snap
    }

    /// Get a mutable reference to the underlying snap function.
    pub fn snap_mut(&mut self) -> &mut SnapFunction<f64> {
        &mut self.snap
    }

    /// Total values processed.
    pub fn count(&self) -> u64 {
        self.count
    }

    /// Total delta events detected.
    pub fn delta_count(&self) -> u64 {
        self.deltas
    }

    /// Fraction of values that were detected as deltas.
    pub fn delta_rate(&self) -> f64 {
        if self.count == 0 {
            return 0.0;
        }
        self.deltas as f64 / self.count as f64
    }

    /// Get the ring buffer, if configured.
    pub fn window(&self) -> Option<&RingBuffer<f64>> {
        self.window.as_ref()
    }

    /// Mean of values in the sliding window, if available.
    pub fn window_mean(&self) -> Option<f64> {
        self.window.as_ref().and_then(|w| w.mean())
    }

    /// Standard deviation of values in the sliding window, if available.
    pub fn window_std_dev(&self) -> Option<f64> {
        self.window.as_ref().and_then(|w| w.std_dev())
    }

    /// Reset all state.
    pub fn reset(&mut self) {
        self.snap.reset();
        self.count = 0;
        self.deltas = 0;
        if let Some(ref mut buf) = self.window {
            *buf = RingBuffer::new(buf.capacity);
        }
    }
}

/// Process a stream of values through an iterator, producing snap results.
///
/// This is the simplest way to process a data stream — just pass any iterator
/// of f64 values and get back an iterator of snap results.
///
/// # Examples
///
/// ```
/// use snapkit::{SnapFunction, process_stream};
///
/// let snap = SnapFunction::<f64>::new();
/// let data = vec![0.05, 0.3, 0.08, 0.5];
///
/// let results: Vec<_> = process_stream(snap, data.into_iter()).collect();
/// assert_eq!(results.len(), 4);
/// assert!(!results[0].is_delta()); // within tolerance
/// assert!(results[1].is_delta());  // delta
/// ```
pub fn process_stream(
    mut snap: SnapFunction<f64>,
    iter: impl Iterator<Item = f64>,
) -> impl Iterator<Item = SnapResult<f64>> {
    iter.map(move |v| snap.observe(v))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ring_buffer() {
        let mut buf = RingBuffer::new(3);
        assert!(buf.is_empty());
        assert!(!buf.is_full());

        buf.push(1.0);
        buf.push(2.0);
        buf.push(3.0);

        assert!(buf.is_full());
        assert_eq!(buf.len(), 3);
        let last_val = buf.last().unwrap();
        assert!((last_val - 3.0_f64).abs() < 1e-10);

        // Overwrite oldest
        buf.push(4.0);
        assert_eq!(buf.len(), 3);
        let last_val = buf.last().unwrap();
        assert!((last_val - 4.0_f64).abs() < 1e-10);
    }

    #[test]
    fn test_ring_buffer_values_order() {
        let mut buf = RingBuffer::new(4);
        buf.push(1.0);
        buf.push(2.0);
        buf.push(3.0);
        buf.push(4.0);

        let vals = buf.values();
        assert_eq!(vals, vec![1.0, 2.0, 3.0, 4.0]);

        // Overwrite with 5,6,7,8
        buf.push(5.0);
        buf.push(6.0);
        buf.push(7.0);
        buf.push(8.0);
        let vals = buf.values();
        assert_eq!(vals, vec![5.0, 6.0, 7.0, 8.0]);
    }

    #[test]
    fn test_ring_buffer_partial() {
        let mut buf = RingBuffer::new(5);
        buf.push(1.0);
        buf.push(2.0);
        let vals = buf.values();
        assert_eq!(vals, vec![1.0, 2.0]);
    }

    #[test]
    fn test_ring_buffer_mean_std() {
        let mut buf = RingBuffer::new(4);
        for v in &[2.0, 4.0, 4.0, 4.0] {
            buf.push(*v);
        }
        assert!((buf.mean().unwrap() - 3.5).abs() < 1e-10);
        // std dev of [2,4,4,4] = 1.0
        assert!((buf.std_dev().unwrap() - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_stream_processor() {
        let snap = SnapFunction::<f64>::new();
        let mut processor = StreamProcessor::new(snap);

        processor.feed(0.05);
        processor.feed(0.02);
        processor.feed(0.3);

        assert_eq!(processor.count(), 3);
        assert_eq!(processor.delta_count(), 1);
        assert!((processor.delta_rate() - 1.0 / 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_stream_processor_with_window() {
        let snap = SnapFunction::<f64>::new();
        let mut processor = StreamProcessor::new(snap).with_window(5);

        for v in &[1.0, 2.0, 3.0, 4.0, 5.0] {
            processor.feed(*v);
        }

        let mean = processor.window_mean().unwrap();
        assert!((mean - 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_process_stream_iterator() {
        let snap = SnapFunction::<f64>::new();
        let data = vec![0.05, 0.3, 0.08, 0.5];
        let results: Vec<_> = process_stream(snap, data.into_iter()).collect();
        assert_eq!(results.len(), 4);
        assert!(results[0].within_tolerance);
        assert!(results[1].is_delta());
    }

    #[test]
    fn test_processor_reset() {
        let snap = SnapFunction::<f64>::new();
        let mut processor = StreamProcessor::new(snap);
        processor.feed(0.3);
        assert_eq!(processor.count(), 1);

        processor.reset();
        assert_eq!(processor.count(), 0);
    }

    #[test]
    fn test_window_access() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(0.5);
        let mut processor = StreamProcessor::new(snap).with_window(3);
        processor.feed(0.1);
        processor.feed(0.2);

        let window = processor.window();
        assert!(window.is_some());
        assert_eq!(window.unwrap().len(), 2);
    }
}
