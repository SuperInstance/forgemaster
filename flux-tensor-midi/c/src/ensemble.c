#include "flux_midi/ensemble.h"
#include <stdlib.h>
#include <string.h>

void ensemble_init(Ensemble* ens, double master_tempo_bpm, int subdivision) {
    memset(ens, 0, sizeof(Ensemble));
    ens->master_tempo_bpm = master_tempo_bpm;
    ens->master_subdivision = subdivision;
    ens->event_buffer = NULL;
    ens->event_buffer_size = 0;
    ens->event_count = 0;
}

void ensemble_free(Ensemble* ens) {
    for (int i = 0; i < ens->n_rooms; i++) {
        room_free(ens->rooms[i]);
        free(ens->rooms[i]);
        ens->rooms[i] = NULL;
    }
    ens->n_rooms = 0;
    free(ens->event_buffer);
    ens->event_buffer = NULL;
}

int ensemble_add_room(Ensemble* ens, RoomMusician* room) {
    if (ens->n_rooms >= ENSEMBLE_MAX_ROOMS) return -1;
    ens->rooms[ens->n_rooms++] = room;
    return 0;
}

int ensemble_remove_room(Ensemble* ens, const char* room_id) {
    for (int i = 0; i < ens->n_rooms; i++) {
        if (strcmp(ens->rooms[i]->room_id, room_id) == 0) {
            room_free(ens->rooms[i]);
            free(ens->rooms[i]);
            for (int j = i; j < ens->n_rooms - 1; j++) {
                ens->rooms[j] = ens->rooms[j + 1];
            }
            ens->n_rooms--;
            return 0;
        }
    }
    return -1;
}

RoomMusician* ensemble_find_room(Ensemble* ens, const char* room_id) {
    for (int i = 0; i < ens->n_rooms; i++) {
        if (strcmp(ens->rooms[i]->room_id, room_id) == 0) {
            return ens->rooms[i];
        }
    }
    return NULL;
}

void ensemble_broadcast(Ensemble* ens, const MidiEvent* event) {
    /* In a real implementation, this would push to each room's event queue.
     * For the core library, we record the event. */
    if (ens->event_count >= ens->event_buffer_size) {
        int new_size = ens->event_buffer_size == 0 ? 64 : ens->event_buffer_size * 2;
        MidiEvent* new_buf = realloc(ens->event_buffer, new_size * sizeof(MidiEvent));
        if (!new_buf) return;
        ens->event_buffer = new_buf;
        ens->event_buffer_size = new_size;
    }
    if (ens->event_count < ens->event_buffer_size) {
        ens->event_buffer[ens->event_count++] = *event;
    }
}

void ensemble_route_signal(Ensemble* ens, const SideSignal* signal) {
    (void)ens; /* Routing logic would go here */
    (void)signal;
}

HarmonyScore* ensemble_harmony_matrix(const Ensemble* ens) {
    int n = ens->n_rooms;
    HarmonyScore* matrix = malloc(n * n * sizeof(HarmonyScore));
    if (!matrix) return NULL;

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (i == j) {
                matrix[i * n + j].jaccard = 1.0;
                matrix[i * n + j].cosine = 1.0;
                matrix[i * n + j].euclidean = 1.0;
                matrix[i * n + j].combined = 1.0;
            } else {
                matrix[i * n + j] = harmony_compute(
                    &ens->rooms[i]->flux, &ens->rooms[j]->flux,
                    1.0, 1.0, 0.5);
            }
        }
    }
    return matrix;
}

double ensemble_average_harmony(const Ensemble* ens) {
    if (ens->n_rooms < 2) return 1.0;

    HarmonyScore* matrix = ensemble_harmony_matrix(ens);
    if (!matrix) return 0.0;

    double total = 0.0;
    int count = 0;
    int n = ens->n_rooms;

    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            total += matrix[i * n + j].combined;
            count++;
        }
    }

    free(matrix);
    return count > 0 ? total / count : 1.0;
}

void ensemble_tick(Ensemble* ens, double t_now) {
    for (int i = 0; i < ens->n_rooms; i++) {
        RoomMusician* rm = ens->rooms[i];
        if (!rm->playing) continue;

        TZeroState state = tzero_check(&rm->clock, t_now);
        if (state == TZERO_ON_TIME) {
            /* Room is on time — potentially emit a tick event */
            MidiEvent evt = midi_note_on(rm->midi_channel, 60, 100, t_now);
            strncpy(evt.source, rm->room_id, sizeof(evt.source) - 1);
            ensemble_broadcast(ens, &evt);
        }
    }
}

void ensemble_tzero_stats(const Ensemble* ens, double t_now,
                          int* on_time, int* late, int* silent, int* dead) {
    *on_time = 0;
    *late = 0;
    *silent = 0;
    *dead = 0;

    for (int i = 0; i < ens->n_rooms; i++) {
        switch (tzero_check(&ens->rooms[i]->clock, t_now)) {
            case TZERO_ON_TIME: (*on_time)++; break;
            case TZERO_LATE:    (*late)++;    break;
            case TZERO_SILENT:  (*silent)++;  break;
            case TZERO_DEAD:    (*dead)++;    break;
        }
    }
}
