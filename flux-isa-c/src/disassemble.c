#include "flux.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *opcode_name(flux_opcode_t op) {
    switch (op) {
    case FLUX_ADD:      return "ADD";
    case FLUX_SUB:      return "SUB";
    case FLUX_MUL:      return "MUL";
    case FLUX_DIV:      return "DIV";
    case FLUX_MOD:      return "MOD";
    case FLUX_ASSERT:   return "ASSERT";
    case FLUX_CHECK:    return "CHECK";
    case FLUX_VALIDATE: return "VALIDATE";
    case FLUX_REJECT:   return "REJECT";
    case FLUX_JUMP:     return "JUMP";
    case FLUX_BRANCH:   return "BRANCH";
    case FLUX_CALL:     return "CALL";
    case FLUX_RETURN:   return "RETURN";
    case FLUX_HALT:     return "HALT";
    case FLUX_LOAD:     return "LOAD";
    case FLUX_STORE:    return "STORE";
    case FLUX_PUSH:     return "PUSH";
    case FLUX_POP:      return "POP";
    case FLUX_SWAP:     return "SWAP";
    case FLUX_SNAP:     return "SNAP";
    case FLUX_QUANTIZE: return "QUANTIZE";
    case FLUX_CAST:     return "CAST";
    case FLUX_PROMOTE:  return "PROMOTE";
    case FLUX_AND:      return "AND";
    case FLUX_OR:       return "OR";
    case FLUX_NOT:      return "NOT";
    case FLUX_XOR:      return "XOR";
    case FLUX_EQ:       return "EQ";
    case FLUX_NEQ:      return "NEQ";
    case FLUX_LT:       return "LT";
    case FLUX_GT:       return "GT";
    case FLUX_LTE:      return "LTE";
    case FLUX_GTE:      return "GTE";
    case FLUX_NOP:      return "NOP";
    case FLUX_DEBUG:    return "DEBUG";
    case FLUX_TRACE:    return "TRACE";
    case FLUX_DUMP:     return "DUMP";
    default:            return "UNKNOWN";
    }
}

void flux_disassemble(const flux_instruction_t *inst, char *dst, size_t dst_size) {
    if (!inst || !dst || dst_size == 0) return;

    int written = 0;

    if (inst->label[0]) {
        written += snprintf(dst + written, dst_size - (size_t)written,
                            "%-10s ", inst->label);
    }

    written += snprintf(dst + written, dst_size - (size_t)written,
                        "%-10s 0x%02X", opcode_name(inst->opcode), (unsigned)inst->opcode);

    for (int i = 0; i < inst->operand_count && written < (int)dst_size - 1; i++) {
        written += snprintf(dst + written, dst_size - (size_t)written,
                            " %.6g", inst->operands[i]);
    }
}

char *flux_disassemble_all(const flux_bytecode_t *bc) {
    if (!bc || bc->instruction_count == 0) {
        char *s = (char *)malloc(1);
        if (s) s[0] = '\0';
        return s;
    }

    /* Over-allocate: each instruction ~128 chars max */
    size_t cap = (size_t)bc->instruction_count * 128 + 1;
    char *buf = (char *)malloc(cap);
    if (!buf) return NULL;

    size_t pos = 0;
    char line[256];
    for (int i = 0; i < bc->instruction_count; i++) {
        snprintf(buf + pos, cap - pos, "%04d: ", i);
        pos += strlen(buf + pos);

        flux_disassemble(&bc->instructions[i], line, sizeof(line));
        size_t line_len = strlen(line);
        if (pos + line_len + 2 >= cap) {
            cap = pos + line_len + 128;
            char *tmp = (char *)realloc(buf, cap);
            if (!tmp) { free(buf); return NULL; }
            buf = tmp;
        }
        memcpy(buf + pos, line, line_len);
        pos += line_len;
        buf[pos++] = '\n';
    }
    buf[pos] = '\0';
    return buf;
}
