idf_component_register(
    SRCS "flux_vm.c" "flux_ops.c" "flux_main.c"
    INCLUDE_DIRS "."
    REQUIRES esp_pm driver esp_timer
)
