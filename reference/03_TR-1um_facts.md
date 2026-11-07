# TR-1um (IP62) 実装制約の実測メモ

`OpenSUSI/TR-1um` および本プロジェクトで使用する標準セル（[`module/STDCELL/`](../module/STDCELL/README.md)）・SRAM マクロ（[`module/SRAM128/`](../module/SRAM128/)）・パッドフレームの実測データ。

## 1. プロセス基本仕様

| 項目 | 値 | 出典 |
|---|---|---|
| ノード | 1 µm CMOS, N-well (`WN`) | `Manifesto.md` |
| 最小ゲート長 L | **1.0 µm** | DR: `AP.LM` / `AN.LM` (1.0–30.0) |
| 最小ゲート幅 W | **3.4 µm** | DR: `AP.WM` / `AN.WM` (3.4–60.0) |
| Tox | **19.5 nm** → 5 V 系 | `models_IP62_mos_v2.lib` |
| Vth | NMOS +0.763 V / PMOS −0.678 V | 同上 |
| 配線層 | **M1 / M2 の2層**（+ ポリゲート `GC`、`V1`、`CO`） | DR table |
| M1 | Wmin 1.8 / Smin 1.4 µm（P&R トラックピッチ **5.4 µm**） | `M1.W1`, `M1.S1` |
| M2 | Wmin 3.0 / Smin 2.0 µm（P&R トラックピッチ **5.4 µm**） | `M2.W1`, `M2.S1` |
| VIA1 (`V1`) | カット `1.4 × 1.4 µm`（M1/M2 包囲 1.0 µm → パッド `3.4 × 3.4 µm`） | `V1.W1`, `V1.enc` |
| デバイス | NMOS / PMOS / NMOSE / 抵抗 `RR`,`RS` / 容量 `CSIO` / ダイオード `DN` | `models` |

---

## 2. ダイ / フレーム（`OSS_FRAME` / `OSS_FRAME_GIO`）

- チップ外形：**2,500 × 2,500 µm**（`pre_check.py`: `CHIP_SIZE_* = 2500.00`、bbox は `(-1250, -1250)` 〜 `(+1250, +1250)` 固定、`dbu = 0.001 µm`）
- 提出 GDSII はトップセル `tr_1um_<github_username>` の下に `OSS_FRAME` を含むこと
- パッド構成：**合計 16 個**
  - 双方向 5V I/O パッド **`OSS_ESD_5V_DIO` × 14**（信号 `P1..P7, P9..P15`）+ `OSS_ESD_5V_VDD` × 1（`P16`）+ `OSS_ESD_5V_VSS` × 1（`P8`）
  - 配置：各辺 4 個、原点から `±200 / ±600 µm`、ボンドパッド中心線 `±1040 µm`
  - 各 `OSS_ESD_5V_DIO` は **ESD 保護ダイオード＋3ステート出力ドライバ（`OUT`, `HIZ`）＋入力端子（`P`）を内蔵**しており、`±920.0 µm` のコア境界上に `3.4 × 3.4 µm` の接続ランドを持つ
- **内側の有効コア領域：`1,840 × 1,840 µm = 3.3856 mm²`**（`(-920, -920)` 〜 `(+920, +920)`）

---

## 3. 実設計採用スタンダードセル [`module/STDCELL/`](../module/STDCELL/README.md)（`v59_4`、行高 59.4 µm）

初期調査時点の旧 `STDLIB/LogicCells`（行高 `62.6 µm`、次節 §4 参照）に代わり、実設計では **サイト幅 `5.4 µm` × 行高 `59.4 µm`（11サイト高）** に高密度化し、`MUXDFFRB`（MUX内蔵FF）・`AOI`/`OAI` 複合ゲート・`BUFTH`（シュミットトリガ入力）・`FILL2/3`（MOSデキャップ）・`TAP2` を完備した **`v59_4` ライブラリ（全 37 CORE セル種）** を採用。

| セル種別 | サイト数 | 幅 W (µm) | 面積 (µm²) | 旧 STDLIB 比 |
|---|---:|---:|---:|---|
| `FILL1` | 1 | 5.4 | 320.8 | — |
| `INV_X1` / `INV_X2` / `TAP2` / `FILL2` | 2 | 10.8 | **641.5** | **0.35 倍**（旧 `1,821.7 µm²`） |
| `NAND2` / `NOR2` / `BUF_X1` / `BUF_X2` / `FILL3` / `TAP3` | 3 | 16.2 | **962.3** | **0.44〜0.53 倍** |
| `NAND3` / `NOR3` / `AND2_X1` / `OR2` / `AOI21` / `OAI21` | 4 | 21.6 | **1,283.0** | **0.59 倍** |
| `NAND4` / `NOR4` / `AND3_X1` / `OR3` / `AOI22` / `OAI22` / `XOR2` / `XNOR2` / `RSLATCH` | 5 | 27.0 | **1,603.8** | **0.56〜0.64 倍** |
| `AND4_X1` / `OR4` / `MUX2` / `BUFTH` / `DEL1` | 6 | 32.4 | **1,924.6** | **0.50〜0.67 倍** |
| `DFF` / `DFFRB` / `DFFS` | 12 | 64.8 | **3,849.1** | **0.61 倍**（旧 `6,297.6 µm²`） |
| **`MUXDFFRB` / `EDFFRB`** | 18 | 97.2 | **5,773.7** | **0.57 倍**（旧 DFFR+MUX2 `10,185 µm²`） |

---

## 4. （参考）初期調査時の旧 `STDLIB/LogicCells`（行高 62.6 µm）

事前見積り（[`04_area_estimation.md`](04_area_estimation.md)）で使用した旧 PDK 同梱セルの実測値（行高 `62.6 µm`）：

| セル | W (µm) | 面積 (µm²) |
|---|---|---|
| INV_X1 / NAND2 / NOR2 / BUF_X1 | 29.1 | **1,821.7** |
| NAND3 / NOR3 / AND2 / OR2 / BUF_X2 | 34.6 | 2,166.0 |
| NAND4 / NOR4 / AND3 / OR3 / INV_X4 | 40.1 | 2,510.3 |
| AND4 / OR4 / XOR2 / XNOR2 / BUF_X4 | 45.6 | 2,854.6 |
| MUX2 / BUF_X8 | 62.1 | 3,887.5 |
| **DFFR / DFFS** | **100.6** | **6,297.6** |
| CLKBUF_X1 / DEL1 | 51.1 | 3,198.9 |

旧ライブラリで不足していた要素（イネーブル/MUX付きFF、シュミットトリガバッファ、AOI/OAI 複合ゲート、Liberty `.lib` / LEF、および 128bit SRAM マクロ）は、すべて [`module/STDCELL/`](../module/STDCELL/README.md) および [`module/SRAM128/`](../module/SRAM128/) にて整備・解決済み。

## 出典

- https://github.com/OpenSUSI/TR-1um
- 本リポジトリ [`module/STDCELL/`](../module/STDCELL/README.md), [`module/SRAM128/`](../module/SRAM128/), [`scripts/pre_check.py`](../scripts/pre_check.py)
