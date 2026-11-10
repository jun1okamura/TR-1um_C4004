# `scripts/` — C4004 設計・配置配線・GDSII 構築・検証 Python スクリプト一覧

本ディレクトリには、`c4004_core` / `OSS_FRAME` のクリティカルパス最適化＆バッファ挿入、OpenROAD 向け2層配線 LEF 生成、11行×3セグメント (`TAP2` 4列) 配置・`FILL3`/`FILL2` 完全充填 (`FILL1 = 0`)、KLayout GDSII アセンブリ、LVS SPICE 生成、および `ngspice` フルチップ抽出検証に使用する Python スクリプト群が格納されています。

---

## 1. スクリプト一覧と役割 (Overview by Design Stage)

| 設計フェーズ | スクリプト名 | 主な役割・機能 | 主な入力 | 主な出力 |
| :--- | :--- | :--- | :--- | :--- |
| **1. 合成後最適化 & バッファ挿入** | [`insert_high_fo_buffers.py`](insert_high_fo_buffers.py) | `X1` `sram_do[3:0] -> MUXDFFRB.A` ゼロゲート直結化、`M1` `d_hiz`/`d_oe` 2段並列デコード化、`sram_ce` 2入力 `NOR2` 化、全7外部入力への `BUFTH` 挿入、行別クロック/リセットツリー構築、高 FO 分割 (`FO <= 10`) | `openroad/c4004_core_raw_syn.v` | `openroad/c4004_core_syn.v`, `openroad/ff_row_map.json` |
| **2. OpenROAD 用 LEF 生成** | [`make_m2only_lef.py`](make_m2only_lef.py) | 標準セルの多角形を矩形分解し、セル内部の `METAL1` を全面 `OBS` 化して信号ピンを `METAL2` のみに限定 (`TR-1um_cells_m2only.lef`) | `module/STDCELL/TR-1um_cells.lef`, `SRAM128.lef` | `openroad/TR-1um_tech_clean.lef`, `openroad/TR-1um_cells_m2only.lef`, `openroad/SRAM128_clean.lef` |
| **3. 11行×3分割配置 & デキャップ充填** | [`run_tap2_flow.py`](run_tap2_flow.py) | 11本の標準セル行を4列の `TAP2` で横3分割 (`108, 109, 108` サイト) パッキングし、クリティカルパスセルのアンカー配置と `FILL3` (223個) + `FILL2` (23個) の完全充填 (**`FILL1 = 0`**) を行い DEF を出力 | `openroad/c4004_core_syn.v`, `openroad/gpl_coords.def` | `openroad/c4004_core_placed.def` |
| **4. 配線ガイド拡張** | [`make_expanded_guide.py`](make_expanded_guide.py) | `openroad/run_grt.tcl` が出力した `route.guide` を11行チャネル幅 (`±81.0 µm`) に拡張し、`openroad/run_apr.tcl` (`detailed_route`) の収束性と配線長を最適化 | `openroad/route.guide` | `openroad/route_expanded.guide` |
| **5. GDSII 構築・電源メッシュ結線** | [`def2gds_chip.py`](def2gds_chip.py) | `apr/c4004_core_routed.def` から標準セル (`618`個)、`SRAM128`、`TAP2` (`44`個)、`FILL3` (`223`個)、`FILL2` (`23`個)、信号配線、`TAP2` 縦 `M2` 電源ストラップ、`SRAM128` 左右電源、両端 `VDDPAD` 接続、4辺 `OSS_FRAME_GIO` `M2` `VSS` ブリッジを統合しフルチップ GDSII を生成 | `apr/c4004_core_routed.def`, PDK/マクロ GDS | `apr/c4004_chip.gds`, `src/tr_1um_jun1okamura.gds` |
| **6. LVS 用 SPICE 生成** | [`v2spice_chip.py`](v2spice_chip.py) | `OSS_ESD_5V_DIO`/`VDD`/`VSS`、`SRAM128`、標準セル、`FILL2`/`FILL3` デキャップを含むフルチップ階層 LVS SPICE ネットリストを生成 | `openroad/c4004_core_syn.v`, `apr/c4004_core_routed.def` | `apr/c4004_chip.spice`, `src/tr_1um_jun1okamura.cir` |
| **7. 抽出 SPICE シミュレーション変換** | [`prep_spice_sim.py`](prep_spice_sim.py) | KLayout LVS が抽出した `apr/OSS_FRAME.extracted` を `ngspice` 互換構文に変換し、`W >= 100 µm` の大サイズ I/O パッド MOSFET をマルチフィンガ (`M=`) 化するとともに素子統計を集計 | `apr/OSS_FRAME.extracted` | `apr/OSS_FRAME_sim.spice`, `apr/simulation/OSS_FRAME.spice` |
| **8. フルチップ `ngspice` 検証 & FMAX** | [`run_spice_tests.py`](run_spice_tests.py) | 抽出ネットリストに対する Test 1 (ALU/DCL)、Test 2 (`SRAM128` Regs)、Test 3 (`SRAM128` Stack & `JCN`) および Test 4 (`1.0〜23.0 MHz` `FMAX` スイープ) を生成・並列実行し、`FMAX = 21.0 MHz`・`t_pd`・消費電力を算出 | `apr/OSS_FRAME_sim.spice` | `apr/sim_test*.sp`, `apr/sim_test*.log` |
| **9. MPW プリチェック** | [`pre_check.py`](pre_check.py), [`read_info.py`](read_info.py) | `info.yaml` と `src/tr_1um_jun1okamura.gds` のトップセル名・DBU (`0.001 µm`)・外形寸法 (`2500 × 2500 µm`) を検証 | `info.yaml`, `src/tr_1um_jun1okamura.gds` | Pre-check 合否判定 |
