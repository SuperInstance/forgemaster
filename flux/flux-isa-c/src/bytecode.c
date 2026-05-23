#include "flux.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Magic: "FLUX" = 0x464C5558 */
#define FLUX_MAGIC   0x464C5558u
#define FLUX_VER_MAJOR 1
#define FLUX_VER_MINOR 0

/* Per-instruction binary layout:
   uint8  opcode
   uint8  operand_count
   uint8  flags (reserved 0)
   uint8  reserved
   double operands[operand_count]          (8 bytes each)
   char   label[32]
*/

static int write_u8(uint8_t **p, const uint8_t *end, uint8_t v) {
    if (*p >= end) return -1;
    *(*p)++ = v;
    return 0;
}
static int write_u16(uint8_t **p, const uint8_t *end, uint16_t v) {
    if (*p + 2 > end) return -1;
    *(*p)++ = (uint8_t)(v & 0xFF);
    *(*p)++ = (uint8_t)((v >> 8) & 0xFF);
    return 0;
}
static int write_u32(uint8_t **p, const uint8_t *end, uint32_t v) {
    if (*p + 4 > end) return -1;
    *(*p)++ = (uint8_t)(v & 0xFF);
    *(*p)++ = (uint8_t)((v >> 8) & 0xFF);
    *(*p)++ = (uint8_t)((v >> 16) & 0xFF);
    *(*p)++ = (uint8_t)((v >> 24) & 0xFF);
    return 0;
}
static int write_f64(uint8_t **p, const uint8_t *end, double v) {
    if (*p + 8 > end) return -1;
    memcpy(*p, &v, 8);
    *p += 8;
    return 0;
}
static int write_bytes(uint8_t **p, const uint8_t *end, const void *src, size_t n) {
    if (*p + n > end) return -1;
    memcpy(*p, src, n);
    *p += n;
    return 0;
}

static int read_u8(const uint8_t **p, const uint8_t *end, uint8_t *v) {
    if (*p + 1 > end) return -1;
    *v = *(*p)++;
    return 0;
}
static int read_u16(const uint8_t **p, const uint8_t *end, uint16_t *v) {
    if (*p + 2 > end) return -1;
    *v = (uint16_t)(**p | ((*p)[1] << 8));
    *p += 2;
    return 0;
}
static int read_u32(const uint8_t **p, const uint8_t *end, uint32_t *v) {
    if (*p + 4 > end) return -1;
    *v = (uint32_t)(*p)[0] | ((uint32_t)(*p)[1] << 8)
       | ((uint32_t)(*p)[2] << 16) | ((uint32_t)(*p)[3] << 24);
    *p += 4;
    return 0;
}
static int read_f64(const uint8_t **p, const uint8_t *end, double *v) {
    if (*p + 8 > end) return -1;
    memcpy(v, *p, 8);
    *p += 8;
    return 0;
}

/* ── Encode ───────────────────────────────────────────────────────── */

size_t flux_bytecode_encode(const flux_bytecode_t *bc, uint8_t **out_buf) {
    if (!bc || !out_buf) return 0;

    /* Header: magic(4) + ver_major(2) + ver_minor(2) + count(4) = 12 bytes */
    /* Per instruction: 4 + operand_count*8 + 32 */
    size_t total = 12;
    for (int i = 0; i < bc->instruction_count; i++) {
        total += 4 + (size_t)bc->instructions[i].operand_count * 8 + 32;
    }

    uint8_t *buf = (uint8_t *)malloc(total);
    if (!buf) return 0;
    uint8_t *p = buf;
    const uint8_t *end = buf + total;

    write_u32(&p, end, FLUX_MAGIC);
    write_u16(&p, end, (uint16_t)FLUX_VER_MAJOR);
    write_u16(&p, end, (uint16_t)FLUX_VER_MINOR);
    write_u32(&p, end, (uint32_t)bc->instruction_count);

    for (int i = 0; i < bc->instruction_count; i++) {
        const flux_instruction_t *inst = &bc->instructions[i];
        write_u8(&p, end, (uint8_t)inst->opcode);
        write_u8(&p, end, (uint8_t)inst->operand_count);
        write_u8(&p, end, 0); /* flags */
        write_u8(&p, end, 0); /* reserved */
        for (int j = 0; j < inst->operand_count; j++)
            write_f64(&p, end, inst->operands[j]);
        /* Pad label to exactly 32 bytes */
        char label[FLUX_LABEL_SIZE];
        memset(label, 0, FLUX_LABEL_SIZE);
        memcpy(label, inst->label, FLUX_LABEL_SIZE);
        write_bytes(&p, end, label, FLUX_LABEL_SIZE);
    }

    *out_buf = buf;
    return (size_t)(p - buf);
}

/* ── Decode ───────────────────────────────────────────────────────── */

int flux_bytecode_decode(const uint8_t *buf, size_t len, flux_bytecode_t *bc) {
    if (!buf || !bc) return -1;

    const uint8_t *p = buf;
    const uint8_t *end = buf + len;

    uint32_t magic;
    if (read_u32(&p, end, &magic) || magic != FLUX_MAGIC) return -2;

    uint16_t major, minor;
    if (read_u16(&p, end, &major)) return -1;
    if (read_u16(&p, end, &minor)) return -1;
    (void)major; (void)minor;

    uint32_t count;
    if (read_u32(&p, end, &count)) return -1;

    bc->capacity = (int)count;
    bc->instruction_count = (int)count;
    bc->instructions = (flux_instruction_t *)calloc((size_t)count, sizeof(flux_instruction_t));
    if (!bc->instructions) return -1;

    for (uint32_t i = 0; i < count; i++) {
        flux_instruction_t *inst = &bc->instructions[i];
        uint8_t opc, oc, flags, reserved;
        if (read_u8(&p, end, &opc)) goto fail;
        if (read_u8(&p, end, &oc))  goto fail;
        if (read_u8(&p, end, &flags)) goto fail;
        if (read_u8(&p, end, &reserved)) goto fail;
        inst->opcode = (flux_opcode_t)opc;
        inst->operand_count = (int)oc;
        if (inst->operand_count > FLUX_MAX_OPERANDS) goto fail;
        for (int j = 0; j < inst->operand_count; j++) {
            if (read_f64(&p, end, &inst->operands[j])) goto fail;
        }
        if (p + FLUX_LABEL_SIZE > end) goto fail;
        memcpy(inst->label, p, FLUX_LABEL_SIZE);
        inst->label[FLUX_LABEL_SIZE - 1] = '\0';
        p += FLUX_LABEL_SIZE;
    }

    return 0;
fail:
    free(bc->instructions);
    bc->instructions = NULL;
    bc->instruction_count = 0;
    bc->capacity = 0;
    return -1;
}
