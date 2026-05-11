/* snapkit.c — single compilation unit for the linked library.
 *
 * Includes all implementation from snapkit.h.
 * Users can also use the single-header mode by defining
 * SNAPKIT_IMPLEMENTATION before including snapkit.h directly.
 */

#define SNAPKIT_IMPLEMENTATION
#include "snapkit.h"

/* All implementation lives in snapkit.h under #ifdef SNAPKIT_IMPLEMENTATION.
   This file simply activates it for the shared/static library build. */
