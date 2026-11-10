set base_dir [file dirname [file dirname [file normalize [info script]]]]
read_lef "$base_dir/openroad/TR-1um_tech_clean.lef"
read_lef "$base_dir/openroad/TR-1um_cells_grt_m1.lef"
read_lef "$base_dir/openroad/SRAM128_clean.lef"

read_def "$base_dir/openroad/c4004_core_placed.def"

set_routing_layers -signal METAL1-METAL2
global_route -guide_file "$base_dir/openroad/route.guide" -congestion_iterations 50 -allow_congestion -verbose
exit
