#ifndef FLUX_MIDI_ENSEMBLE_H
#define FLUX_MIDI_ENSEMBLE_H

#ifdef __cplusplus
extern "C" {
#endif

#include "room.h"
#include "midi_event.h"
#include "sidechannel.h"
#include "harmony.h"

/*
 * Ensemble — the full band of RoomMusicians.
 *
 * Manages a collection of rooms, routes events between them,
 * and computes ensemble-level metrics.
 */

#define ENSEMBLE_MAX_ROOMS 128

typedef struct {
    RoomMusician*  rooms[ENSEMBLE_MAX_ROOMS];
    int            n_rooms;
    double         master_tempo_bpm;
    int            master_subdivision;  /* PPQN */
    double         session_start_time;
    MidiEvent*     event_buffer;
    int            event_buffer_size;
    int            event_count;
} Ensemble;

/* Initialize ensemble */
void ensemble_init(Ensemble* ens, double master_tempo_bpm, int subdivision);

/* Free ensemble and all rooms */
void ensemble_free(Ensemble* ens);

/* Add a room to the ensemble. Returns 0 on success, -1 on full. */
int ensemble_add_room(Ensemble* ens, RoomMusician* room);

/* Remove a room by ID. Returns 0 on success, -1 if not found. */
int ensemble_remove_room(Ensemble* ens, const char* room_id);

/* Find a room by ID. Returns pointer or NULL. */
RoomMusician* ensemble_find_room(Ensemble* ens, const char* room_id);

/* Broadcast an event to all rooms in the ensemble */
void ensemble_broadcast(Ensemble* ens, const MidiEvent* event);

/* Route a side-channel signal to target (or broadcast if target is empty) */
void ensemble_route_signal(Ensemble* ens, const SideSignal* signal);

/* Compute pairwise harmony matrix. Caller must free the returned array.
 * Returns NULL on failure. */
HarmonyScore* ensemble_harmony_matrix(const Ensemble* ens);

/* Compute average ensemble harmony (mean of all pairwise scores) */
double ensemble_average_harmony(const Ensemble* ens);

/* Tick the entire ensemble: check all T-0 clocks, emit events */
void ensemble_tick(Ensemble* ens, double t_now);

/* Get the number of rooms in each T-0 state */
void ensemble_tzero_stats(const Ensemble* ens, double t_now,
                          int* on_time, int* late, int* silent, int* dead);

#ifdef __cplusplus
}
#endif

#endif /* FLUX_MIDI_ENSEMBLE_H */
