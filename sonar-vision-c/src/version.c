/*
 * version.c — SonarVision version string
 */

#include "sonar_vision.h"

static const char VERSION[] = "1.0.0";

const char *sv_version(void)
{
    return VERSION;
}
