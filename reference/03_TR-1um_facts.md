# TR-1um (IP62) 実装制約の実測メモ

`OpenSUSI/TR-1um` (@ main, 2026-09-08 clone) と本テンプレートから抽出した実データ。

## 1. プロセス

| 項目 | 値 | 出典 |
|---|---|---|
| ノード | 1 µm CMOS, N-well (`WN`) | Manifesto.md |
| 最小ゲート長 L | **1.0 µm** | DR: `AP.LM` / `AN.LM` (1.0–30.0) |
| 最小ゲート幅 W | **3.4 µm** | DR: `AP.WM` / `AN.WM` (3.4–60.0) |
| Tox | **19.5 nm** → 5 V 系 | `models_IP62_mos_v2.lib` |
| Vth | NMOS +0.763 V / PMOS −0.678 V | 同上 |
| 配線層 | **M1 / M2 の2層**（+ ポリゲート GC、V1、CO） | DR table |
| M1 | Wmin 1.8 / Smin 1.4 µm → pitch 3.2 µm | `M1.W1`, `M1.S1` |
| M2 | Wmin 3.0 / Smin 2.0 µm → pitch 5.0 µm | `M2.W1`, `M2.S1` |
| Drawing layer | 8層（従来 17マスク+6認識層を簡素化） | Manifesto.md |
| デバイス | NMOS/PMOS(通常・空乏型) / 抵抗 RR,RS / 容量 CSIO / ダイオード | models |

## 2. ダイ / フレーム（`TR-1um_frame_25x25.gds`）

- チップ枠 **2,500 × 2,500 µm**（`pre_check.py`: `CHIP_SIZE_*=2500.00`、bbox は ±1250 固定）
- トップセルは `OSS_FRAME` または `OSS_FRAME_TEG` を必ず含むこと
- パッド: **合計16個**
  - `OSS_ESD_5V_ANA` × 14（信号）+ `OSS_ESD_5V_VDD` × 1 + `OSS_ESD_5V_VSS` × 1
  - 配置: 各辺 4個、原点から ±200 / ±600 µm、辺の中心線 ±1040 µm
  - ESD セル外形 400 × 240 µm（`OSS_PAD` 開口 100 × 100 µm）
- コーナー `OSS_FRAME_CNR` 360 × 360 µm を四隅に配置
- **内側の有効コア領域 ≒ 1,840 × 1,840 µm = 3.39 mm²**（四隅を避けると実効 ~3.0 mm²）

> **重要**: パッドセルは ESD のみ。**入力バッファ／出力ドライバ／3ステートバッファは
> 設計者側で用意する必要がある**（4004 の D0–D3 双方向バスに必須）。

## 3. スタンダードセル `STDLIB/LogicCells`（GDS 実測）

行高 **62.6 µm** 固定。

| セル | W (µm) | 面積 (µm²) |
|---|---|---|
| INV_X1 / NAND2 / NOR2 / BUF_X1 | 29.1 | **1,821.7** |
| NAND3 / NOR3 / AND2 / OR2 / BUF_X2 | 34.6 | 2,166.0 |
| NAND4 / NOR4 / AND3 / OR3 / INV_X4 | 40.1 | 2,510.3 |
| AND4 / OR4 / XOR2 / XNOR2 / BUF_X4 | 45.6 | 2,854.6 |
| MUX2 / BUF_X8 | 62.1 | 3,887.5 |
| **DFFR / DFFS** | **100.6** | **6,297.6** |
| CLKBUF_X1 / DEL1 | 51.1 | 3,198.9 |
| CLKBUF_X16 | 392.1 | 24,545.5 |

ラインナップ: INV/BUF/CLKBUF (X1,2,4,8,12,16), NAND2-4, NOR2-4, AND2-4, OR2-4,
XOR2, XNOR2, MUX2, DEL1/2/4, **DFFR, DFFS**

**不足しているもの（4004 実装で問題になる）**
- ラッチ（D-latch / transparent latch）が無い → 2相ラッチ設計ができない
- **イネーブル付き FF が無い** → `DFFE` は DFF + MUX2 で作る必要（+3,887.6 µm²/bit）
- 3ステートバッファ・バスキーパが無い
- AOI/OAI 複合ゲートが無い
- Liberty (.lib) / LEF が無い → **合成・P&R 用ライブラリは自作が必要**（`lef/` の役割）
- SRAM/ROM マクロが無い

## 出典

- https://github.com/OpenSUSI/TR-1um （Document/TR-1um_Drawing_Layer_DR_Table.csv, Manifesto.md,
  libs.tech/spice/models/, libs.tech/klayout/libraries/TR-1um_frame_25x25.gds, STDLIB/LogicCells/gds/）
- 本リポジトリ `scripts/pre_check.py`
