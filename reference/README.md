# `reference/` — 設計調査資料・実装記録

OpenSUSI TR-1um（1 µm CMOS、2層配線 `M1`/`M2`、`5.0 V`）プロセスによる Intel 4004 互換 CPU（`C4004`）の事前フィージビリティ調査から、6T SRAM マクロ（`SRAM128`）設計、OpenROAD 2層チャネル配置配線、DRC/LVS サインオフ、および実レイアウト抽出後（Post-Layout Extracted）フルチップ `ngspice` 検証までの技術資料一式です。

| ファイル | 内容 |
| :--- | :--- |
| [`01_Intel4004_spec.md`](01_Intel4004_spec.md) | Intel 4004 のスペック・アーキテクチャ・ピン配置・MCS-4 ファミリ仕様 |
| [`02_CMOS_implementations.md`](02_CMOS_implementations.md) | CMOS/HDL 実装事例（Tiny Tapeout SKY130 版、OpenCores `mcs-4`、4004.com 等） |
| [`03_TR-1um_facts.md`](03_TR-1um_facts.md) | TR-1um (IP62) の実測制約：デザインルール、`OSS_FRAME_GIO` パッド、`module/STDCELL` (`v59_4`) セル面積 |
| [`04_area_estimation.md`](04_area_estimation.md) | 初期面積見積り（旧 STDLIB でのストレート合成 3.80 mm² → 課題抽出と圧縮方針） |
| [`05_cell_circuits.md`](05_cell_circuits.md) | **最小構成 CMOS 回路集**: 単相クロック / `DLATCH` / `MUXDFFRB` / レジスタ・スタックアレイ / I/O |
| [`06_design_policy.md`](06_design_policy.md) | **設計方針まとめ（最終確定版反映）**: 16ピン割当 / RTL ルール / `BUFTH`・高FOツリー / 2層P&R・`TAP2` 3分割方針 |
| [`07_sram6t_macro.md`](07_sram6t_macro.md) | **6T SRAM マクロ構成 (`SRAM128`)**: 32w×4b 構成・アドレスマップ・6T セル設計・周辺回路・実マクロ仕様 |
| [`08_senseamp_refs.md`](08_senseamp_refs.md) | **センスアンプ文献集（1 µm 世代）**: 特許8件・JSSC 論文・書籍・トポロジ比較・オフセット設計 |
| [`09_work_memo.md`](09_work_memo.md) | **実設計・検証ログ総括**: `SRAM128` 検証、RTL〜Yosys 合成、OpenROAD 2層配線、`TAP2`/`FILL2/3` 統合、DRC/LVS、Post-Layout `ngspice` & `FMAX` 解析 |

---

## 要旨（事前調査から最終実装までの結論）

1. **ピン数とフレームの完全一致**:
   - オリジナル 4004（16ピン DIP）に対し、クロックを単相（`P1 = clk`）化することで空いた1ピンを外部バスバッファ方向制御用の `d_oe`（`P9`）に割り当て、**TR-1um の `OSS_FRAME_GIO`（双方向パッド `OSS_ESD_5V_DIO` ×14 + `VDD` + `VSS` = 16パッド）に完全収容**。
2. **面積ボトルネックの解消（`3.80 mm²` → 実セル＋マクロ合計 `1.07 mm²`）**:
   - 旧標準セル（行高 `62.6 µm`）で全レジスタを FF 合成すると素セル面積 `3.80 mm²` となりコア領域（`1,840 × 1,840 µm = 3.39 mm²`）に収まらなかったが、以下の3施策で解決：
     1. **6T SRAM ハードマクロ [`module/SRAM128`](../module/SRAM128/)（`32w × 4b = 128 bit`, `1166.1 × 185.6 µm = 0.2164 mm²`）** にインデックスレジスタ（`16 × 4-bit`）とサブルーチンスタック（`3 × 12-bit`）を集約。
     2. **高密度標準セルライブラリ [`module/STDCELL`](../module/STDCELL/README.md)（`v59_4`, 行高 `59.4 µm`, サイト幅 `5.4 µm`）** と 2:1 MUX 内蔵 FF（`MUXDFFRB` ×29個）を採用し、順序回路を計 **40 FF** に削減。
     3. **OpenROAD 2層チャネル配置配線**: 9本のアクティブ行間に2行分（`118.8 µm` = 22トラック）の水平 `M1` 配線チャネルを設け、`TAP2` 縦4列でコアを横3分割（`108 / 109 / 108` サイト）、空き領域に MOS デキャップ `FILL3`（29個）・`FILL2`（13個）を充填。
3. **最終サインオフ・実レイアウト抽出後性能**:
   - **総素子数**: **`6,180` 素子**（MOSFET `6,152` 個 + ESD ダイオード `28` 個、総フィンガ数 `6,440`）、総配置セル **`722` 個**。
   - **DRC / LVS**: KLayout DRC エラー **`0` 件**、フルチップ階層/フラット LVS **完全一致 (`Match`)**。
   - **最大動作周波数 (`FMAX`)**: 実レイアウト抽出ネット (`OSS_FRAME.extracted`) の `ngspice` シミュレーションにて **フルチップ `FMAX = 15.0 MHz`**（オリジナル 4004 `740 kHz` の **約20倍**、コア論理単体 `25.0 MHz`）、消費電力 `15.2 mW @ 10 MHz` / `22.7 mW @ 15 MHz` (`VDD = 5.0 V`) を達成。

---

## 主要リンク

- https://en.wikipedia.org/wiki/Intel_4004
- https://en.wikichip.org/wiki/intel/mcs-4/4004
- https://www.4004.com/ / https://4004.com/mcs4-masks-schematics-sim.html
- https://tinytapeout.com/chips/ttsky25a/tt_um_mcs4_cpu
- https://github.com/munetomo-maruyama/MCS4_SYSTEM
- https://opencores.org/projects/mcs-4 / https://github.com/freecores/mcs-4
- https://github.com/OpenSUSI/TR-1um
