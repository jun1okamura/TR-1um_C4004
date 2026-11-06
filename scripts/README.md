# `scripts/` — C4004 設計・配置配線・GDSII 構築・検証 Python スクリプト一覧

本ディレクトリには、`c4004_core` / `OSS_FRAME` のネットリストバッファ挿入、OpenROAD 向け2層配線 LEF 生成、配置配線・ピン再終端、KLayout GDSII アセンブリ、LVS SPICE 生成、DRC/LVS 検証、および `ngspice` フルチップ抽出検証・統計抽出に使用した Python スクリプト群が格納されています。

---

## 1. スクリプト一覧と役割 (Overview by Design Stage)

| 設計フェーズ | スクリプト名 | 主な役割・機能 | 主な入力 | 主な出力 |
| :--- | :--- | :--- | :--- | :--- |
| **1. 合成後バッファ挿入** | [`insert_high_fo_buffers.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/insert_high_fo_buffers.py) | 全7外部入力へのシュミットトリガ `BUFTH` 挿入、行別クロック (`clk_buf_r*`)・リセット (`rst_n_buf_r*`) ツリー構築、`FO >= 8` 信号の空間2分割 `BUF_X2` 挿入 | `c4004_core_raw.v`, 配置座標 | `openroad/c4004_core_buffered_or.v`, `syn/c4004_core.v` |
| **2. OpenROAD 用 LEF 生成** | [`make_clean_lefs.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/make_clean_lefs.py) | PDK LEF の `POLYGON` を矩形 (`RECT`) に分解、DFF 内部ノード (`CKB/CKP/QM/QS`) を `OBS` 化、`VDD/VSS` レールを `M1 OBS` に変換 | `TR-1um_cells.lef` | `openroad/TR-1um_cells_or.lef`, `openroad/TR-1um_cells_grt_fullobs.lef` |
| **2. OpenROAD 用 LEF 生成** | [`make_m2only_lef.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/make_m2only_lef.py) | 2層配線での標準セル内 `M1` ショートを完全防止するため、セル内部 `y = 1.1..58.3 µm` の `M1` を全面 `OBS` 化し、信号ピンを `METAL2` のみに限定 | `openroad/TR-1um_cells_or.lef` | `openroad/TR-1um_cells_m2only.lef` |
| **3. OpenROAD 配置・配線** | [`run_tap2_flow.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/run_tap2_flow.py) | 9本の標準セル行を4列の `TAP2` で横3分割 (`108, 109, 108` サイト) パッキングし、OpenROAD `global_route` → `81 µm` チャネルガイドスナップ → `detailed_route` を自動実行 | `openroad/placed_test4edge_1v.def`, `openroad/*.lef` | `openroad/tap2_exact_pos.tcl`, `openroad/placed_tap2.def`, `openroad/route_tap2_strict.guide`, `openroad/routed_tap2.def` |
| **4. 境界ピン整合・再配線** | [`reterminate_tap2_nets.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/reterminate_tap2_nets.py) | 全19本のコア境界ピンを `OSS_FRAME_GIO` パッド座標に厳密整合させ、`TAP2` 縦 `M2` 領域のローカル競合を 3D グリッド (`5.4 µm` ピッチ) ダイクストラ法で解消 | `openroad/routed_tap2.def` | `apr/c4004_core_4edge_routed.def` |
| **5. GDSII 構築・電源配線** | [`build_core_and_chip_gds.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/build_core_and_chip_gds.py) | 標準セル、`SRAM128`、`TAP2` (36個)、`FILL3` (29個) / `FILL2` (13個) / `FILL1` (3個)、信号配線、`TAP2` 縦 `M2` 電源ストラップ、`SRAM128` 左右電源、`VDDPAD`・`OSS_FRAME_GIO` `M2` `VSS` ブリッジを統合し GDSII を出力 | `apr/c4004_core_4edge_routed.def`, `OSS_FRAME.gds`, `SRAM128.gds`, `TR-1um_v59_4.gds` | `apr/c4004_core_routed.gds`, `apr/c4004_chip.gds` |
| **6. LVS 用 SPICE 生成** | [`build_lvs_spice.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/build_lvs_spice.py) | `OSS_ESD_5V_DIO`/`VDD`/`VSS`、`SRAM128`、標準セル、`FILL2`/`FILL3` デキャップを含むフルチップ階層 LVS SPICE ネットリストを生成し KLayout LVS を検証 | `openroad/c4004_core_buffered_or.v`, `apr/c4004_core_4edge_routed.def` | `apr/c4004_chip.spice`, `apr/simulation/OSS_FRAME.spice`, `src/OSS_FRAME.cir` |
| **7. 物理検証 (DRC/導通)** | [`verify_core_and_chip.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/verify_core_and_chip.py) | KLayout `pya` API によるフルチップ DRC チェック (`M1`/`M2`/`V1`/`WN`/50nm グリッド/`PTECT`) および `LayoutToNetlist` によるパッド〜コア間の全ネット導通・ショート検証 | `apr/c4004_chip.gds`, `apr/c4004_core_routed.gds` | コンソール検証レポート (DRC 0件・Open/Short 0件) |
| **8. 抽出 SPICE 変換** | [`prep_extracted_ngspice.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/prep_extracted_ngspice.py) | KLayout が抽出した `apr/OSS_FRAME.extracted` を `ngspice` 互換構文に変換し、`W >= 100 µm` の大サイズ I/O パッド MOSFET をマルチフィンガ (`M=`) 化してモデルビンに適合させる | `apr/OSS_FRAME.extracted`, PDK SPICE モデル | `apr/simulation/OSS_FRAME_extracted_sim.spice`, `apr/simulation/models.spice` |
| **9. フルチップ検証 & FMAX** | [`run_chip_verif.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/run_chip_verif.py) | 抽出ネットリストに対する3種の機能検証テストベンチ (`tb_chip_1_func`, `tb_chip_2_sram`, `tb_chip_3_stack_jcn`) および `10〜40 MHz` `FMAX` スイープを生成し、ローカル並列実行・波形解析 | `apr/simulation/OSS_FRAME_extracted_sim.spice` | `apr/simulation/tb_chip_*.spice`, `apr/simulation/verif_summary.json` |
| **10. 統計集計 (回路/物理)** | [`compile_full_stats.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/compile_full_stats.py)<br/>[`compile_gds_stats.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/compile_gds_stats.py) | `OSS_FRAME.extracted` と `c4004_chip.gds` からサブサーキット別・フラット素子数、フィンガ数、ネット数、面積、`VIA1` 数を集計 | `apr/OSS_FRAME.extracted`, `apr/c4004_chip.gds` | `apr/simulation/extracted_full_stats.json`, `apr/simulation/gds_physical_stats.json` |
| **11. MPW CI プリチェック** | [`pre_check.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/pre_check.py)<br/>[`read_info.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/read_info.py) | OpenSUSI MPW テンプレート標準の `info.yaml` 読込および提出用 GDSII (`src/OSS_FRAME.gds`) のトップセル名・DBU・外形バウンディングボックス検査 | `info.yaml`, `src/OSS_FRAME.gds` | CI Pre-check 判定結果 |

---

## 2. 各スクリプトの詳細説明

### 2.1 `insert_high_fo_buffers.py`
- **目的**: 外部パッドからの長距離配線や高ファンアウトネットによるスルーレート劣化・グリッチを防ぐため、論理合成後のネットリスト (`c4004_core_raw.v`) にバッファツリーを挿入します。
- **処理内容**:
  1. 外部入力ピン (`clk`, `rst`, `test`, `d_in[0:3]`) の直後にシュミットトリガバッファ `BUFTH` (`clk_ibuf`, `rst_ibuf`, `test_ibuf`, `din_ibuf_0..3`) を挿入。
  2. クロック (`clk`) および内部リセット (`rst_n`) に対し、標準セル行ごとに専用の `BUF_X2` リーフバッファ (`clk_buf_r0..r9`, `rst_n_buf_r0..r9`) を割り当て、1バッファあたりの駆動負荷を最大10シンク以下に制限。
  3. ファンアウト8以上のすべての内部制御・アドレス・データ信号に対し、接続先セルの X 座標で左右2グループに空間クラスタリングした `BUF_X2` バッファペア (`*_b0`, `*_b1`) を自動挿入。

### 2.2 `make_clean_lefs.py` / `make_m2only_lef.py`
- **目的**: OpenROAD の Global Router (`FastRoute`) および Detailed Router (`TritonRoute`) が 2層配線 (`M1`, `M2`) の TR-1um 標準セルを DRC エラーなく配線できるよう LEF を最適化します。
- **処理内容**:
  - `make_clean_lefs.py`: PDK 標準の `TR-1um_cells.lef` に含まれる非直交・多角形 `POLYGON` 定義を水平矩形 (`RECT`) に厳密分解し、フリップフロップ (`DFF_X1`, `DFFR_X1`, `DFFS_X1`) の内部配線ピン (`CKB`, `CKP`, `QM`, `QS`) を `OBS` に移動します。また GRT 用の `TR-1um_cells_grt_fullobs.lef` を生成します。
  - `make_m2only_lef.py`: 標準セル内部（`y = 1.1..58.3 µm`）の `METAL1` を全面 `OBS` としてマスクし、各信号ピンの `METAL2` ポート（または `VIA1` 位置の `METAL2` パッド）のみをピンとして公開する `TR-1um_cells_m2only.lef` を生成します。これにより、ルータは必ず垂直 `M2` でセルピンにアクセスし、水平 `M1` トランクは行間の空きチャネル（`118.8 µm` 幅）のみを通るようになります。

### 2.3 `run_tap2_flow.py`
- **目的**: 標準セル領域を4列の `TAP2`（`x = 21.6, 615.6, 1215.0, 1809.0 µm`）で横方向に3分割（各セグメント `108, 109, 108` サイト）し、さらに空きスペースが `FILL3`（3サイト）および `FILL2`（2サイト）で効率良く埋まるように2〜3サイト単位でセル間隔を配分した上で、OpenROAD の Global Route と Detailed Route を実行します。
- **処理内容**:
  1. 9本のアクティブ行 (`y = 59.4, 237.6, ..., 1485.0 µm`) ごとに、元の配置順序を維持したまま3つのセグメントにセルを割り当て、`openroad/tap2_exact_pos.tcl` を出力。
  2. OpenROAD を起動して `openroad/placed_tap2.def` と初期ガイド `openroad/route_tap2.guide` を生成（`openroad/run_grt.tcl` 相当）。
  3. ガイドボックスを `81.0 µm` チャネルグリッドにスナップした `openroad/route_tap2_strict.guide` を生成し、再度 OpenROAD を起動して Detailed Route を実行し `openroad/routed_tap2.def` を出力（`openroad/run_drt.tcl` 相当）。

### 2.4 `reterminate_tap2_nets.py`
- **目的**: OpenROAD で配線された `routed_tap2.def` の19本のコア境界ピンを、`OSS_FRAME_GIO` の4辺パッド引き出し座標に厳密一致させ、`TAP2` 縦 `M2` ストラップ領域とのわずかな干渉を解消します。
- **出力**: `apr/c4004_core_4edge_routed.def`（DRC 0件・全657信号ネット完全開通）。

### 2.5 `build_core_and_chip_gds.py`
- **目的**: `apr/c4004_core_4edge_routed.def` から KLayout `pya` を用いてコア GDSII (`apr/c4004_core_routed.gds`) とフルチップ GDSII (`apr/c4004_chip.gds`) を構築します。
- **実装される電源・フィラー構造**:
  - 4列×9行 = **36個の `TAP2`** セル配置と、各列上の縦方向 `M2` `VDD`/`VSS` ストラップ配線。
  - 空きサイトへのデキャップフィラー自動充填（**`FILL3` × 29個**、**`FILL2` × 13個**、1サイト隙間のみ **`FILL1` × 3個**）。
  - `SRAM128` の左右両側の `VDD`/`VSS` ピンとコア `VDD`/`VSS` タップ配線の双方向接続。
  - 左右両端の `TAP2` `VDD` から北辺 `VDDPAD` (`P16`) への広幅 `M1`/`M2` 接続。
  - 全標準セル行および `TAP2` 列の `VSS` と、4辺の `OSS_FRAME_GIO` `M2` `VSS` リングとの多点ブリッジ接続。

### 2.6 `build_lvs_spice.py` & `verify_core_and_chip.py`
- **`build_lvs_spice.py`**: `OSS_FRAME` トップレベルの階層 SPICE ネットリスト (`apr/c4004_chip.spice`, `apr/simulation/OSS_FRAME.spice`, `src/OSS_FRAME.cir`) を生成します。`OSS_ESD_5V_DIO`, `OSS_ESD_5V_VDD`, `OSS_ESD_5V_VSS`, `SRAM128`, 標準セル、および MOS キャパシタを持つ `FILL2`/`FILL3` インスタンスをすべて含み、KLayout LVS で 100% 一致します。
- **`verify_core_and_chip.py`**: KLayout の DRC エンジンと `LayoutToNetlist` を呼び出し、`M1`/`M2`/`VIA1`/`WN`/50nm グリッド/`PTECT` の全 DRC ルールおよび19本のパッド〜コア信号＋`VDD`/`VSS` の導通をスタンドアロンで検査します。

### 2.7 `prep_extracted_ngspice.py`, `run_chip_verif.py`, `compile_full_stats.py`, `compile_gds_stats.py`
- **`prep_extracted_ngspice.py`**: KLayout LVS が抽出した `apr/OSS_FRAME.extracted` を読み込み、`ngspice` 用のサブサーキット・モデル定義 (`apr/simulation/OSS_FRAME_extracted_sim.spice`, `apr/simulation/models.spice`) を生成します。
- **`run_chip_verif.py`**: 抽出フルチップネットリストに対し、外部 ROM/RAM エミュレータと `1.0 pF` パッド負荷を接続した3本の機能検証テストベンチ (`tb_chip_1_func.spice`, `tb_chip_2_sram.spice`, `tb_chip_3_stack_jcn.spice`) と `10〜40 MHz` の `FMAX` スイープテストベンチを生成し、`ngspice -b` で並列実行して遅延・消費電流・`FMAX` を集計します。
- **`compile_full_stats.py` / `compile_gds_stats.py`**: 抽出ネットリストと GDSII から素子数（`6,180` 素子 / `6,440` フィンガ）、ネット数（`2,892` フラットネット）、セル数（`722` セル）、`VIA1` 数（`13,884` 個）を集計し JSON に出力します。
