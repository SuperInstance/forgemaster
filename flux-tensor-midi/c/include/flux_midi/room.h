#ifndef FLUX_MIDI_ROOM_H
#define FLUX_MIDI_ROOM_H

#ifdef __cplusplus
extern "C" {
#endif

#include "flux.h"
#include "clock.h"

/*
 * RoomMusician — a PLATO room participating in the ensemble.
 *
 * Each room is a "musician" with its own clock, flux state, and
 * listening connections. Rooms communicate via MIDI events and
 * side-channel signals (nods, smiles, frowns).
 */

#define ROOM_ID_MAX    64
#define ROOM_INST_MAX  32
#define ROOM_LISTEN_MAX 32

typedef struct {
    char room_id[ROOM_ID_MAX];
    char instrument[ROOM_INST_MAX];
    TZeroClock clock;
    FluxVector flux;
    double tempo_bpm;
    int    subdivision;    /* PPQN (pulses per quarter note) */
    int    midi_channel;   /* 1-16 */
    int    playing;        /* 1 = active, 0 = stopped */
    char*  listening_to[ROOM_LISTEN_MAX];
    int    n_listening;
} RoomMusician;

/* Initialize a room musician */
void room_init(RoomMusician* rm, const char* room_id, const char* instrument,
               double tempo_bpm, int subdivision, int midi_channel);

/* Free dynamically allocated listening list */
void room_free(RoomMusician* rm);

/* Add a room to the listening list. Returns 0 on success, -1 on full. */
int room_listen_to(RoomMusician* rm, const char* target_room_id);

/* Remove a room from the listening list. Returns 0 on success, -1 if not found. */
int room_stop_listening(RoomMusician* rm, const char* target_room_id);

/* Check if this room is listening to a given room */
int room_is_listening(const RoomMusician* rm, const char* target_room_id);

/* Start/stop playing */
void room_start(RoomMusician* rm);
void room_stop(RoomMusician* rm);

/* Update the room's flux vector */
void room_update_flux(RoomMusician* rm, const FluxVector* new_flux);

/* Get the room's current quarter-note interval in seconds */
double room_quarter_interval(const RoomMusician* rm);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_ROOM_H */
