# `module/STDCELL/` — OpenSUSI TR-1um 標準セルライブラリ (`v59_4`, 行高 59.4 µm)

本ディレクトリには、`C4004` の論理合成・自動配置配線・GDSII 生成・LVS 検証に使用する **TR-1um 5V 標準セルライブラリ（行高 `59.4 µm`、サイト幅 `5.4 µm`、全 37 CORE セル種）** が格納されています。

---

## 1. ファイル構成

| ファイル / ディレクトリ | 内容・用途 |
| :--- | :--- |
| [`TR-1um_STDCELL.gds`](TR-1um_STDCELL.gds) | 全 37 種の標準セル（論理・順序 32 種 + フィラー/デキャップ `FILL1`〜`FILL3` + ウェルタップ `TAP2`, `TAP3`）の GDSII レイアウト |
| [`tr1um_typ_5v0_25c.lib`](tr1um_typ_5v0_25c.lib) | Yosys 論理合成および OpenROAD STA 用 Liberty タイミングライブラリ (`VDD = 5.0 V`, `25 °C`, Typical) |
| [`TR-1um_cells.lef`](TR-1um_cells.lef) | 原型標準セル LEF（[`scripts/make_clean_lefs.py`](../../scripts/make_clean_lefs.py) / [`scripts/make_m2only_lef.py`](../../scripts/make_m2only_lef.py) の入力） |
| [`TR-1um_tech.lef`](TR-1um_tech.lef) | 原型テクノロジ LEF (`SITE TR1UM`, `METAL1`, `VIA1`, `METAL2`) |
| [`cell_info.json`](cell_info.json) | 全 37 セルのサイト数・外形寸法 (`width_um`, `height_um`) 定義 JSON |
| [`simulation/*.spice`](simulation/) | 素子を持つ全 34 セル（論理 32 種 + アクティブデキャップ `FILL2`, `FILL3`）の LVS / シミュレーション用 SPICE サブサーキット定義 |

---

## 2. 収録標準セル一覧（全 37 種）

| カテゴリ | 収録セル (`*` は `C4004` 実使用セル：計 30 種) |
| :--- | :--- |
| **順序回路 (FF / Latch)** | `MUXDFFRB`*, `DFFRB`*, `DFFS`*, `DFF`, `EDFFRB`, `RSLATCH`, `TLAT` |
| **バッファ / インバータ / 遅延** | `BUFTH`* (シュミットトリガ入力), `BUF_X2`*, `BUF_X1`, `INV_X1`*, `INV_X2`*, `DEL1` |
| **基本論理ゲート** | `NAND2`*, `NAND3`*, `NAND4`*, `NOR2`*, `NOR3`*, `NOR4`*, `AND2_X1`*, `AND3_X1`*, `AND4_X1`*, `OR2`*, `OR3`*, `OR4`* |
| **複合ゲート / MUX / EXOR** | `AOI21`*, `AOI22`*, `OAI21`*, `OAI22`*, `MUX2`*, `XOR2`*, `XNOR2`* |
| **物理セル (Tap / Filler)** | `TAP2`*, `TAP3`, `FILL3`* (MOS Decap), `FILL2`* (MOS Decap), `FILL1`* (Spacer) |
