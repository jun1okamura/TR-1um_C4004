#!/usr/bin/env python3
"""
Extract physical layout statistics from apr/c4004_chip.gds to complement
the extracted netlist statistics from apr/OSS_FRAME.extracted.
"""
import os
import json
from collections import Counter
import pya

WORKSPACE = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004"
CHIP_GDS = os.path.join(WORKSPACE, "apr/c4004_chip.gds")
OUT_JSON = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/gds_physical_stats.json"


def main():
    ly = pya.Layout()
    ly.read(CHIP_GDS)
    dbu = ly.dbu

    top = ly.cell("OSS_FRAME")
    core = ly.cell("c4004_core")
    sram = ly.cell("SRAM128")

    top_bbox = top.bbox()
    core_bbox = core.bbox()
    sram_bbox = sram.bbox()

    # Count direct child instances of c4004_core in GDS (includes TAP2, FILL1, FILL2, FILL3)
    core_inst_counts = Counter()
    core_cell_areas_um2 = Counter()
    for inst in core.each_inst():
        cname = ly.cell(inst.cell_index).name
        core_inst_counts[cname] += 1
        cb = ly.cell(inst.cell_index).bbox()
        area = (cb.width() * dbu) * (cb.height() * dbu)
        core_cell_areas_um2[cname] += area

    # Count CONT (12,0), M1 (13,0), VIA (19,0), M2 (20,0) shapes in c4004_core and full chip
    idx_cont = ly.layer(12, 0)
    idx_m1 = ly.layer(13, 0)
    idx_via = ly.layer(19, 0)
    idx_m2 = ly.layer(20, 0)

    core_top_vias = core.shapes(idx_via).size()
    core_top_conts = core.shapes(idx_cont).size()
    chip_top_vias = top.shapes(idx_via).size()

    # Recursive flat shape counts across entire chip
    r_cont_all = pya.Region(top.begin_shapes_rec(idx_cont))
    r_via_all = pya.Region(top.begin_shapes_rec(idx_via))
    total_conts_chip = r_cont_all.count()
    total_vias_chip = r_via_all.count()

    # Measure M1 and M2 area in c4004_core (top-level routing)
    r_m1_core = pya.Region(core.shapes(idx_m1))
    r_m2_core = pya.Region(core.shapes(idx_m2))
    r_m1_core.merge()
    r_m2_core.merge()

    stats = {
        "die_width_um": round(top_bbox.width() * dbu, 2),
        "die_height_um": round(top_bbox.height() * dbu, 2),
        "die_area_mm2": round((top_bbox.width() * dbu) * (top_bbox.height() * dbu) / 1e6, 4),
        "core_width_um": round(core_bbox.width() * dbu, 2),
        "core_height_um": round(core_bbox.height() * dbu, 2),
        "core_area_mm2": round((core_bbox.width() * dbu) * (core_bbox.height() * dbu) / 1e6, 4),
        "sram128_width_um": round(sram_bbox.width() * dbu, 2),
        "sram128_height_um": round(sram_bbox.height() * dbu, 2),
        "sram128_area_mm2": round((sram_bbox.width() * dbu) * (sram_bbox.height() * dbu) / 1e6, 4),
        "core_gds_instances": dict(core_inst_counts),
        "core_total_gds_instances": sum(core_inst_counts.values()),
        "core_routing_vias": core_top_vias,
        "core_routing_conts": core_top_conts,
        "chip_top_vias": chip_top_vias,
        "total_chip_conts_flat": total_conts_chip,
        "total_chip_vias_flat": total_vias_chip,
        "core_m1_area_um2": round(r_m1_core.area() * (dbu ** 2), 1),
        "core_m2_area_um2": round(r_m2_core.area() * (dbu ** 2), 1),
    }

    with open(OUT_JSON, "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
