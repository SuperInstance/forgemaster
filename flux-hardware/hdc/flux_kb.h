#ifndef FLUX_HDC_KB_H
#define FLUX_HDC_KB_H
#include <stdint.h>

#define HDC_DIM 1024
#define HDC_NUM_CONCEPTS 7

typedef struct __attribute__((aligned(64))) {
    uint64_t fingerprint;
    uint64_t folded_vector[2];  // 128-bit folded HDC
    uint32_t concept_id;
    uint8_t padding[36];
} HdcRecord;

static inline float hdc_similarity(const HdcRecord* a, uint64_t query[2]) {
    int matching = 0;
    for (int i = 0; i < 2; i++) {
        matching += __builtin_popcountll(~(a->folded_vector[i] ^ query[i]));
    }
    return (float)matching / 128.0f;
}

static const HdcRecord flux_hdc_kb[HDC_NUM_CONCEPTS] = {
    {0xD648F385D7B07AC5ULL, {0xB6DA2C1216A78288ULL, 0xC89A365E848690AFULL}, 0},  // temperature
    {0x00267913D62AEA2CULL, {0x0E0FC328D022D775ULL, 0x89157248CEEF4F56ULL}, 1},  // altitude
    {0xB88B7ED540F958ADULL, {0x665FCE2DFC246A3DULL, 0x4FEC3CEAD1826A78ULL}, 2},  // airspeed
    {0xB3FBB472EF4FE4EDULL, {0x6562F9F8D1A43B7FULL, 0x5C2B3293E9A94C7EULL}, 3},  // fuel_flow
    {0x83A6D8FFA3A724B2ULL, {0xBBA44B974D36BDFCULL, 0xB1F829B0F6E5A053ULL}, 4},  // oil_temp
    {0xAE50CF24F6C7F529ULL, {0xC10CAC1AAAA0B186ULL, 0x96A99FDD81F2380BULL}, 5},  // battery_v
    {0x486E22EBBEEEE985ULL, {0x5BEBB690DCA5145EULL, 0x322D3F38C5D01CD5ULL}, 6},  // cabin_pressure
};

#endif