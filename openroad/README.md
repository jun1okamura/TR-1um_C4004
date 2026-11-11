# `openroad/` — OpenROAD & Yosys 設定ファイル・LEF・スクリプト一覧

本ディレクトリには、OpenSUSI TR-1um（1 µm CMOS、2層金属配線 `M1`/`M2`）プロセスにおいて `c4004_core`（`637` 標準セル＋`SRAM128` マクロ＝`638` 論理インスタンス、全 `715` 信号ネット）を DRC エラーおよびセル内ショート皆無で自動配置配線するための **OpenROAD 設定ファイル（LEF、Tcl スクリプト、ルーティングガイド、DEF）** および **Yosys 論理合成・ロックステップ検証ファイル** がまとめられています。

---

## 1. ファイル一覧 (File Inventory)

### 1.1 Yosys 論理合成 & ゲートレベル検証

| ファイル名 | 説明 |
| :--- | :--- |
| [`synth.ys`](synth.ys) | Yosys 論理合成スクリプト。`rtl/c4004_core.v`（Plan B v2：全出力 FF 直出し＋事前演算レジスタ駆動 `SRAM128` 制御＋専用並列キャリー `pc_inc`＋MCS-4 `25/25` 完全準拠）を読み込み、`dffe_map.v` によりイネーブル付 FF を `MUXDFFRB` に直接マッピングし、クリティカル出力・`SRAM128` 直受けキャプチャ FF を純 `DFFRB` に保持して TR-1um 標準セル (`tr1um_typ_5v0_25c.lib`) + `SRAM128.lib` に合成します。 |
| [`dffe_map.v`](dffe_map.v) | Yosys の `$_DFFE_*` セルを TR-1um の `MUXDFFRB` セルへ直接マッピングするための techmap ルール。 |
| [`c4004_core_raw_syn.v`](c4004_core_raw_syn.v) | `synth.ys` が生成する初期ゲートレベルネットリスト（`589` セル）。 |
| [`c4004_core_syn.v`](c4004_core_syn.v) | [`scripts/insert_high_fo_buffers.py`](../scripts/insert_high_fo_buffers.py) により、全7外部入力へのシュミットトリガ `BUFTH`、`SRAM128.DO[3:0]` 直受けキャプチャ FF (`u_ff_sram_lat0..3`) 用の `3 × BUF_X2` (`+4.35 ns`) Useful-Skew クロックチェーン、エッジ固定出力 `DFFRB`（12個）、行別クロック/リセットツリー、および空間分割バッファ (`BUF_X2`, `FO <= 10`) を挿入した最終ゲートレベルネットリスト（`637` 標準セル + `1` `SRAM128` = `638` インスタンス、順序回路 `67` FF [`MUXDFFRB: 40`, `DFFRB: 27`]）。 |
| [`primitives.v`](primitives.v), [`tb_lockstep.v`](tb_lockstep.v) | RTL (`rtl/c4004_core.v`) とゲートレベルネットリスト (`openroad/c4004_core_syn.v`) を34クロックのハードウェア `SRAM128` ゼロクリアを含む280クロックフェーズにわたりサイクル単位で完全一致検証（Lockstep 0 errors）するためのテストベンチ。 |

### 1.2 OpenROAD 用テクノロジ・セル・マクロ LEF ファイル

| ファイル名 | 説明 |
| :--- | :--- |
| [`TR-1um_tech_clean.lef`](TR-1um_tech_clean.lef) | OpenROAD 用テクノロジ LEF。サイト `CoreSite` (`5.4 µm × 59.4 µm`)、水平配線層 `METAL1` (ピッチ `5.4 µm`)、層間ビア `V1`、垂直配線層 `METAL2` (ピッチ `5.4 µm`) を定義。 |
| [`TR-1um_cells_grt_m1.lef`](TR-1um_cells_grt_m1.lef) | **Global Route (`run_grt.tcl`) 用標準セル LEF**。GCell 境界の混雑エラーを回避しつつ大域トポロジを生成するための LEF。 |
| [`TR-1um_cells_m2only.lef`](TR-1um_cells_m2only.lef) | **Detailed Route (`run_apr.tcl`) 用標準セル LEF**。セル内部の `METAL1` を全面 `OBS` にすると同時に、全標準セルの信号ピンを `LAYER METAL2` パッドのみに限定し、セル内 `M1` ショートを物理的にゼロにします。 |
| [`SRAM128_clean.lef`](SRAM128_clean.lef) | `32×4-bit` SRAM ハードマクロ (`1166.1 × 185.6 µm`) の OpenROAD 用 LEF。 |

### 1.3 OpenROAD 実行 Tcl スクリプト・ガイド・DEF

| ファイル名 | 説明 |
| :--- | :--- |
| [`c4004_core_placed.def`](c4004_core_placed.def) | [`scripts/run_tap2_flow.py`](../scripts/run_tap2_flow.py)（Lagrangian 行割当 + Simulated Annealing セル順序最適化）が出力した、11行×3セグメント (`TAP2` 4列 = `44`個、行ピッチ `145.8 µm`) 配置＋アクティブデキャップ (`FILL3`×108, `FILL2`×21 = `129`個、`366`サイト、**`FILL1`×0**) 完全充填済みの配置 DEF（全 `811` コンポーネント、論理占有率 `89.76%` [`3,209 / 3,575` サイト]、全 `715` 信号ネット、Legalized HPWL `275,880 µm`）。 |
| [`run_grt.tcl`](run_grt.tcl) | **OpenROAD Global Route 実行スクリプト** (`openroad -exit openroad/run_grt.tcl`)。`c4004_core_placed.def` を読み込み、初期ルーティングガイド `route.guide` を出力します。 |
| [`route_expanded.guide`](route_expanded.guide) | [`scripts/make_expanded_guide.py`](../scripts/make_expanded_guide.py) により `route.guide` を11行チャネル幅に拡張した詳細配線ガイド。 |
| [`run_apr.tcl`](run_apr.tcl) | **OpenROAD Detailed Route 実行スクリプト** (`openroad -exit openroad/run_apr.tcl`)。`TR-1um_cells_m2only.lef`、`c4004_core_placed.def`、`route_expanded.guide` を読み込み、TritonRoute (`detailed_route`) で全 `715` ネットを詳細配線して `apr/c4004_core_routed.def`（**DRC 違反 `0` 件、総配線長 `409,187 µm` [`M1: 180,012 µm`, `M2: 229,175 µm`]、総信号ビア `2,900` 個**）を出力します。 |

---

## 2. スタンドアロン実行手順 (How to Run)

リポジトリルートから以下のコマンドで合成から自動配置配線・GDSII 生成までを一貫実行できます。

```bash
# 1. Yosys 論理合成 & クリティカルパス最適化・バッファ挿入
yosys -s openroad/synth.ys
python3 scripts/insert_high_fo_buffers.py

# 2. 11行×3セグメント (TAP2 4列) 配置 & FILL3/FILL2 完全充填 (FILL1=0)
python3 scripts/run_tap2_flow.py

# 3. OpenROAD Global Route -> Guide 拡張 -> Detailed Route (0 DRC)
openroad -exit openroad/run_grt.tcl
python3 scripts/make_expanded_guide.py
openroad -exit openroad/run_apr.tcl

# 4. フルチップ GDSII & LVS SPICE ネットリスト生成
klayout -b -r scripts/def2gds_chip.py
python3 scripts/v2spice_chip.py
```
