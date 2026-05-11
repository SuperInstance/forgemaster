/// Side-channel communication: non-verbal signals between musicians in a PLATO room.
///
/// Side-channels carry sub-musical information — nods, smiles, and frowns —
/// that express approve/disapprove/acknowledge states without altering the
/// primary MIDI data stream.
pub mod nod;
pub mod smile;
pub mod frown;
