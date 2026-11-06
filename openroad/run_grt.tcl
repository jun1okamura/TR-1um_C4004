# OpenROAD Floorplan, 9-Row Channel Setup, TAP2 3-Way Partition Placement, and Global Routing
# Usage: openroad -exit openroad/run_grt.tcl

set repo_dir [file normalize [file dirname [info script]]/..]
set or_dir "$repo_dir/openroad"

read_lef "$or_dir/TR-1um_tech_or.lef"
read_lef "$or_dir/TR-1um_cells_grt_fullobs.lef"
read_lef "$or_dir/SRAM128_or.lef"
read_liberty "$repo_dir/module/SRAM128/SRAM128.lib"
read_verilog "$or_dir/c4004_core_buffered_or.v"
link_design c4004_core

# Initialize 1840.0 x 1840.0 um core floorplan and 5.4 um M1/M2 routing tracks
initialize_floorplan -die_area "0 0 1840.0 1840.0" -core_area "21.6 0.0 1819.8 1805.6" -site TR1UM
make_tracks METAL1 -y_offset 2.7 -y_pitch 5.4
make_tracks METAL2 -x_offset 2.7 -x_pitch 5.4

# Place SRAM128 macro at top of core
place_macro -macro_name u_sram -location {334.8 1596.0} -orientation R0 -exact
cut_rows -halo_width_x 21.6 -halo_width_y 10.0

# Place 19 core boundary pins across 4 edges aligned with OSS_FRAME_GIO pads
foreach item {{d_in[0] 332.1} {d_out[0] 353.7} {d_in[1] 688.5} {d_out[1] 710.1} {d_hiz 888.3} {d_in[2] 1044.9} {d_out[2] 1066.5} {d_in[3] 1401.3} {d_out[3] 1422.9}} {
  place_pin -pin_name [lindex $item 0] -layer METAL1 -location [list 0.0 [lindex $item 1]] -pin_size {1.8 1.8} -force_to_die_boundary
}
foreach item {{cm_ram[0] 332.1} {cm_ram[1] 688.5} {cm_ram[2] 1044.9} {cm_ram[3] 1401.3}} {
  place_pin -pin_name [lindex $item 0] -layer METAL1 -location [list 1840.0 [lindex $item 1]] -pin_size {1.8 1.8} -force_to_die_boundary
}
foreach item {{sync 288.9} {clk 299.7} {cm_rom 1557.9}} {
  place_pin -pin_name [lindex $item 0] -layer METAL2 -location [list [lindex $item 1] 1840.0] -pin_size {3.4 3.4} -force_to_die_boundary
}
foreach item {{rst 288.9} {d_oe 1093.5} {test 1460.7}} {
  place_pin -pin_name [lindex $item 0] -layer METAL2 -location [list [lindex $item 1] 0.0] -pin_size {3.4 3.4} -force_to_die_boundary
}

# Keep every 3rd standard-cell row (9 active rows separated by 118.8 um 2-row horizontal routing channels)
set block [ord::get_db_block]
set kept_rows {}
set idx 0
foreach row [$block getRows] {
  set bbox [$row getBBox]
  set ry [$bbox yMin]
  if {$ry >= 1550000 || [expr {$idx % 3}] != 1} {
    odb::dbRow_destroy $row
  } else {
    lappend kept_rows $row
  }
  incr idx
}

# Apply exact 3-segment TAP2-aware standard-cell coordinates
source "$or_dir/tap2_exact_pos.tcl"
foreach inst [$block getInsts] {
  if {[$inst isFixed]} { continue }
  set iname [$inst getName]
  set xy [dict get $exact_tap2_pos $iname]
  $inst setOrient R0
  $inst setLocation [lindex $xy 0] [lindex $xy 1]
  $inst setPlacementStatus PLACED
}

# Block METAL1 inside active standard-cell rows and METAL2 inside the 4 vertical TAP2 columns
set_routing_layers -signal METAL1-METAL2 -clock METAL1-METAL2
set m1_layer [[$block getTech] findLayer METAL1]
set m2_layer [[$block getTech] findLayer METAL2]
foreach r $kept_rows {
  set rbbox [$r getBBox]
  odb::dbObstruction_create $block $m1_layer 21600 [expr {[$rbbox yMin] + 1100}] 1819800 [expr {[$rbbox yMax] - 1100}]
}
foreach tx {21600 615600 1215000 1809000} {
  odb::dbObstruction_create $block $m2_layer [expr {$tx + 1000}] 59400 [expr {$tx + 9800}] 1544400
}

set_global_routing_layer_adjustment METAL1 0.0
global_route -congestion_iterations 50 -guide_file "$or_dir/route_tap2.guide" -verbose
write_def "$or_dir/placed_tap2.def"
