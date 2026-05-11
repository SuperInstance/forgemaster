#include "flux_midi/room.h"
#include <stdlib.h>
#include <string.h>

void room_init(RoomMusician* rm, const char* room_id, const char* instrument,
               double tempo_bpm, int subdivision, int midi_channel) {
    memset(rm, 0, sizeof(RoomMusician));
    strncpy(rm->room_id, room_id, ROOM_ID_MAX - 1);
    rm->room_id[ROOM_ID_MAX - 1] = '\0';
    strncpy(rm->instrument, instrument, ROOM_INST_MAX - 1);
    rm->instrument[ROOM_INST_MAX - 1] = '\0';
    rm->tempo_bpm = tempo_bpm;
    rm->subdivision = subdivision;
    rm->midi_channel = midi_channel;
    rm->playing = 0;
    rm->n_listening = 0;

    /* Initialize clock with quarter-note interval */
    double interval = 60.0 / tempo_bpm;
    tzero_init(&rm->clock, interval, 0.3, 1);

    /* Initialize zero flux */
    flux_zero(&rm->flux);
}

void room_free(RoomMusician* rm) {
    for (int i = 0; i < rm->n_listening; i++) {
        free(rm->listening_to[i]);
        rm->listening_to[i] = NULL;
    }
    rm->n_listening = 0;
}

int room_listen_to(RoomMusician* rm, const char* target_room_id) {
    if (rm->n_listening >= ROOM_LISTEN_MAX) return -1;
    if (room_is_listening(rm, target_room_id)) return 0; /* already listening */

    char* copy = strdup(target_room_id);
    if (!copy) return -1;
    rm->listening_to[rm->n_listening++] = copy;
    return 0;
}

int room_stop_listening(RoomMusician* rm, const char* target_room_id) {
    for (int i = 0; i < rm->n_listening; i++) {
        if (strcmp(rm->listening_to[i], target_room_id) == 0) {
            free(rm->listening_to[i]);
            /* Shift remaining */
            for (int j = i; j < rm->n_listening - 1; j++) {
                rm->listening_to[j] = rm->listening_to[j + 1];
            }
            rm->n_listening--;
            rm->listening_to[rm->n_listening] = NULL;
            return 0;
        }
    }
    return -1;
}

int room_is_listening(const RoomMusician* rm, const char* target_room_id) {
    for (int i = 0; i < rm->n_listening; i++) {
        if (strcmp(rm->listening_to[i], target_room_id) == 0) return 1;
    }
    return 0;
}

void room_start(RoomMusician* rm) { rm->playing = 1; }
void room_stop(RoomMusician* rm) { rm->playing = 0; }

void room_update_flux(RoomMusician* rm, const FluxVector* new_flux) {
    rm->flux = *new_flux;
}

double room_quarter_interval(const RoomMusician* rm) {
    return 60.0 / rm->tempo_bpm;
}
