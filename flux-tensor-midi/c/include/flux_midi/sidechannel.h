#ifndef FLUX_MIDI_SIDECHANNEL_H
#define FLUX_MIDI_SIDECHANNEL_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Side-Channel Signals — non-verbal ensemble communication.
 *
 * Nods:   acknowledgment, "I hear you", ready to proceed
 * Smiles: approval, harmony, positive reinforcement
 * Frowns: dissonance, disagreement, negative feedback
 *
 * These are lightweight signals that don't carry payload,
 * just intent. Think of them as the glances between musicians
 * in a jazz combo.
 */

typedef enum {
    SIDE_NOD   = 0,
    SIDE_SMILE = 1,
    SIDE_FROWN = 2
} SideChannelType;

typedef struct {
    SideChannelType type;
    double   timestamp;
    char     source[64];     /* Room that sent the signal */
    char     target[64];     /* Room that receives (empty = broadcast) */
    double   intensity;      /* [0..1], how strong the signal */
} SideSignal;

/* Initialize a side-channel signal */
void side_signal_init(SideSignal* s, SideChannelType type,
                      const char* source, const char* target,
                      double timestamp, double intensity);

/* Create a nod signal */
SideSignal side_nod(const char* source, const char* target,
                    double timestamp, double intensity);

/* Create a smile signal */
SideSignal side_smile(const char* source, const char* target,
                      double timestamp, double intensity);

/* Create a frown signal */
SideSignal side_frown(const char* source, const char* target,
                      double timestamp, double intensity);

/* Check if a signal is a broadcast (empty target) */
int side_is_broadcast(const SideSignal* s);

/* Get human-readable signal type name */
const char* side_type_name(SideChannelType t);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_SIDECHANNEL_H */
