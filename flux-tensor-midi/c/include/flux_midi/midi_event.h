#ifndef FLUX_MIDI_MIDI_EVENT_H
#define FLUX_MIDI_MIDI_EVENT_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * MIDI Event — unified event type for the ensemble.
 *
 * Carries both traditional MIDI (note on/off, CC) and
 * side-channel signals (nod, smile, frown).
 */

typedef enum {
    MIDI_NOTE_ON   = 0,
    MIDI_NOTE_OFF  = 1,
    MIDI_CC        = 2,
    MIDI_NOD       = 3,
    MIDI_SMILE     = 4,
    MIDI_FROWN     = 5,
    MIDI_CLOCK     = 6,
    MIDI_START     = 7,
    MIDI_STOP      = 8,
    MIDI_PROGRAM   = 9
} MidiEventType;

typedef struct {
    MidiEventType event_type;
    int           channel;    /* 1-16 */
    double        timestamp;  /* Seconds since epoch or session start */
    int           pitch;      /* 0-127 (note events) */
    int           velocity;   /* 0-127 */
    int           cc_number;  /* 0-127 (CC events) */
    int           cc_value;   /* 0-127 */
    int           program;    /* 0-127 (program change) */
    double        duration;   /* Seconds (note events) */
    char          source[64]; /* Source room_id */
} MidiEvent;

/* Initialize a zero event */
void midi_event_init(MidiEvent* e);

/* Create a note-on event */
MidiEvent midi_note_on(int channel, int pitch, int velocity, double timestamp);

/* Create a note-off event */
MidiEvent midi_note_off(int channel, int pitch, double timestamp);

/* Create a CC event */
MidiEvent midi_cc(int channel, int cc_number, int cc_value, double timestamp);

/* Create a side-channel event (nod/smile/frown) */
MidiEvent midi_sidechannel(MidiEventType type, int channel, double timestamp);

/* Compare events by timestamp (for qsort) */
int midi_event_compare(const void* a, const void* b);

/* Get human-readable event type name */
const char* midi_event_type_name(MidiEventType t);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_MIDI_EVENT_H */
