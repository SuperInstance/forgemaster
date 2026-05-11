#include "flux_midi/midi_event.h"
#include <string.h>

void midi_event_init(MidiEvent* e) {
    memset(e, 0, sizeof(MidiEvent));
}

MidiEvent midi_note_on(int channel, int pitch, int velocity, double timestamp) {
    MidiEvent e;
    midi_event_init(&e);
    e.event_type = MIDI_NOTE_ON;
    e.channel = channel;
    e.pitch = pitch;
    e.velocity = velocity;
    e.timestamp = timestamp;
    return e;
}

MidiEvent midi_note_off(int channel, int pitch, double timestamp) {
    MidiEvent e;
    midi_event_init(&e);
    e.event_type = MIDI_NOTE_OFF;
    e.channel = channel;
    e.pitch = pitch;
    e.timestamp = timestamp;
    return e;
}

MidiEvent midi_cc(int channel, int cc_number, int cc_value, double timestamp) {
    MidiEvent e;
    midi_event_init(&e);
    e.event_type = MIDI_CC;
    e.channel = channel;
    e.cc_number = cc_number;
    e.cc_value = cc_value;
    e.timestamp = timestamp;
    return e;
}

MidiEvent midi_sidechannel(MidiEventType type, int channel, double timestamp) {
    MidiEvent e;
    midi_event_init(&e);
    e.event_type = type;
    e.channel = channel;
    e.timestamp = timestamp;
    return e;
}

int midi_event_compare(const void* a, const void* b) {
    const MidiEvent* ea = (const MidiEvent*)a;
    const MidiEvent* eb = (const MidiEvent*)b;
    if (ea->timestamp < eb->timestamp) return -1;
    if (ea->timestamp > eb->timestamp) return 1;
    return 0;
}

const char* midi_event_type_name(MidiEventType t) {
    switch (t) {
        case MIDI_NOTE_ON:  return "note_on";
        case MIDI_NOTE_OFF: return "note_off";
        case MIDI_CC:       return "cc";
        case MIDI_NOD:      return "nod";
        case MIDI_SMILE:    return "smile";
        case MIDI_FROWN:    return "frown";
        case MIDI_CLOCK:    return "clock";
        case MIDI_START:    return "start";
        case MIDI_STOP:     return "stop";
        case MIDI_PROGRAM:  return "program";
        default:            return "unknown";
    }
}
