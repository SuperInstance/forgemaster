#include "flux_midi/room.h"
#include "flux_midi/ensemble.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>

#define ASSERT_FEQ(a, b, eps) do { \
    double _a = (a), _b = (b), _eps = (eps); \
    if (fabs(_a - _b) > _eps) { \
        fprintf(stderr, "FAIL %s:%d: %.6f != %.6f (eps=%.6f)\n", \
                __FILE__, __LINE__, _a, _b, _eps); \
        return 1; \
    } \
} while(0)

int test_room_init(void) {
    RoomMusician rm;
    room_init(&rm, "oracle1", "synth", 120.0, 24, 1);
    assert(strcmp(rm.room_id, "oracle1") == 0);
    assert(strcmp(rm.instrument, "synth") == 0);
    ASSERT_FEQ(rm.tempo_bpm, 120.0, 1e-12);
    assert(rm.midi_channel == 1);
    assert(rm.playing == 0);
    assert(rm.n_listening == 0);
    ASSERT_FEQ(room_quarter_interval(&rm), 0.5, 1e-12);
    printf("  PASS test_room_init\n");
    room_free(&rm);
    return 0;
}

int test_room_listen(void) {
    RoomMusician rm;
    room_init(&rm, "room_a", "bass", 100.0, 24, 2);

    assert(room_listen_to(&rm, "room_b") == 0);
    assert(room_listen_to(&rm, "room_c") == 0);
    assert(rm.n_listening == 2);
    assert(room_is_listening(&rm, "room_b") == 1);
    assert(room_is_listening(&rm, "room_d") == 0);

    /* Duplicate should not add */
    assert(room_listen_to(&rm, "room_b") == 0);
    assert(rm.n_listening == 2);

    assert(room_stop_listening(&rm, "room_b") == 0);
    assert(rm.n_listening == 1);
    assert(room_is_listening(&rm, "room_b") == 0);

    assert(room_stop_listening(&rm, "nonexistent") == -1);
    printf("  PASS test_room_listen\n");
    room_free(&rm);
    return 0;
}

int test_room_start_stop(void) {
    RoomMusician rm;
    room_init(&rm, "test", "drums", 140.0, 24, 10);
    assert(rm.playing == 0);
    room_start(&rm);
    assert(rm.playing == 1);
    room_stop(&rm);
    assert(rm.playing == 0);
    printf("  PASS test_room_start_stop\n");
    room_free(&rm);
    return 0;
}

int test_ensemble(void) {
    Ensemble ens;
    ensemble_init(&ens, 120.0, 24);

    RoomMusician* r1 = malloc(sizeof(RoomMusician));
    RoomMusician* r2 = malloc(sizeof(RoomMusician));
    room_init(r1, "room_1", "piano", 120.0, 24, 1);
    room_init(r2, "room_2", "bass", 120.0, 24, 2);

    assert(ensemble_add_room(&ens, r1) == 0);
    assert(ensemble_add_room(&ens, r2) == 0);
    assert(ens.n_rooms == 2);

    RoomMusician* found = ensemble_find_room(&ens, "room_1");
    assert(found == r1);
    assert(ensemble_find_room(&ens, "nonexistent") == NULL);

    /* With identical zero flux: Jaccard=1.0 (no active channels), cosine=0.0 (zero vectors).
     * Combined harmony uses weights (1,1,0.5) so: (1*1.0 + 1*0.0 + 0.5*1.0)/2.5 = 0.6 */
    double avg = ensemble_average_harmony(&ens);
    ASSERT_FEQ(avg, 0.6, 1e-12);

    /* Give different flux */
    r1->flux.channels[0].salience = 1.0;
    r1->flux.channels[1].salience = 1.0;
    r2->flux.channels[0].salience = 1.0;
    r2->flux.channels[2].salience = 1.0;
    avg = ensemble_average_harmony(&ens);
    assert(avg > 0.0 && avg < 1.0);

    printf("  PASS test_ensemble\n");
    ensemble_free(&ens);
    return 0;
}

int main(void) {
    printf("=== Room & Ensemble Tests ===\n");
    int fails = 0;
    fails += test_room_init();
    fails += test_room_listen();
    fails += test_room_start_stop();
    fails += test_ensemble();
    printf(fails == 0 ? "All tests passed.\n" : "%d test(s) FAILED.\n", fails);
    return fails;
}
