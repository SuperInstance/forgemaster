#include "flux_midi/sidechannel.h"
#include <string.h>

void side_signal_init(SideSignal* s, SideChannelType type,
                      const char* source, const char* target,
                      double timestamp, double intensity) {
    memset(s, 0, sizeof(SideSignal));
    s->type = type;
    s->timestamp = timestamp;
    s->intensity = intensity;
    if (source) strncpy(s->source, source, sizeof(s->source) - 1);
    if (target) strncpy(s->target, target, sizeof(s->target) - 1);
}

SideSignal side_nod(const char* source, const char* target,
                    double timestamp, double intensity) {
    SideSignal s;
    side_signal_init(&s, SIDE_NOD, source, target, timestamp, intensity);
    return s;
}

SideSignal side_smile(const char* source, const char* target,
                      double timestamp, double intensity) {
    SideSignal s;
    side_signal_init(&s, SIDE_SMILE, source, target, timestamp, intensity);
    return s;
}

SideSignal side_frown(const char* source, const char* target,
                      double timestamp, double intensity) {
    SideSignal s;
    side_signal_init(&s, SIDE_FROWN, source, target, timestamp, intensity);
    return s;
}

int side_is_broadcast(const SideSignal* s) {
    return s->target[0] == '\0';
}

const char* side_type_name(SideChannelType t) {
    switch (t) {
        case SIDE_NOD:   return "nod";
        case SIDE_SMILE: return "smile";
        case SIDE_FROWN: return "frown";
        default:         return "unknown";
    }
}
