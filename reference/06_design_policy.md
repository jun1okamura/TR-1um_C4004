# C4004 設計方針とセルライブラリ計画

確定日: 2026-09-08。根拠は `03_TR-1um_facts.md`（PDK実測）/
`04_area_estimation.md`（面積見積り）/ `05_cell_circuits.md`（回路）。

## 1. 確定した3つの方針

| # | 方針 | 理由 |
|---|---|---|
| 1 | **クロックは単相**（φ1/φ2 の2相は廃止） | クロック分配が単純。φ2 が不要になりパッドが1本空く |
| 2 | **3ステートは GIO（双方向I/Oセル）でのみ使用** | 内部3ステートバスは検証・LVS・ESD の負担が大きい。内部は MUX 化 |
| 3 | **レジスタファイル + PC/スタック（112bit）はスクラッチのカスタムアレイ** | DFFE で作ると 1.14 mm²。カスタムなら 0.12 mm² |

## 2. ピン割当（16パッド = 信号14 + VDD + VSS）

| 信号 | 方向 | 本数 | 備考 |
|---|---|---|---|
| `D[3:0]` | inout | 4 | **GIO セル**（`oe` で Hi-Z） |
| `SYNC_N` | out | 1 | |
| `CM_ROM_N` | out | 1 | |
| `CM_RAM_N[3:0]` | out | 4 | |
| `TEST` | in | 1 | |
| `RESET_N` | in | 1 | |
| `CLK` | in | 1 | **単相** |
| 予備 | — | 1 | CLKOUT / スキャン(SI or SO) / デバッグに割当可 |
| `VDD` / `VSS` | — | 2 | `OSS_ESD_5V_VDD` / `OSS_ESD_5V_VSS` |

オリジナル 4004 は φ1/φ2 で 16ピン丁度だったが、単相化で **1本余る**。

## 3. RTL 記述ルール（`hdl/`）

1. **`always @(posedge CLK)` のみ**。φ1/φ2 は使わない。
   オリジナルの 8 ステート `A1 A2 A3 M1 M2 X1 X2 X3` は
   **CLK 同期の 3bit ステートカウンタ**で生成する。
2. **`inout` はトップ `c4004_top` にのみ置く**。
   コア内部は `dout / oe / din` の3信号に分離し、内部バスは MUX で構成。
   `assign bus = oe ? x : 1'bz;` のような記述をコア内に書かない。
3. **レジスタファイルとスタックを FF 配列で書かない**。
   `c4004_regfile`（16w×4b）と `c4004_stack`（4w×12b）を
   **ブラックボックスモジュール**として切り出す。
   - RTL では behavioral モデル、実装ではカスタムアレイに差し替え
   - I/F: `WA/WD/WE`(+`WWL`) と `RA/RD`
   - PC の +1 は **アレイ外の 12bit インクリメンタ**で read → +1 → write back
4. **イネーブルは 4bit（ワード）単位でまとめる**。
   bit ごとにイネーブルを散らすと `DFFR+MUX2 = 10,185 µm²/bit` になる。
   4bit 単位なら **ICG 1個 + 素DFF×4 = 16,700 µm²/4bit** が最小（§5 参照）。

## 4. 検証フロー

| 段階 | ツール | 置き場所 |
|---|---|---|
| RTL 機能検証 | Icarus Verilog / Verilator + Busicom 141-PF 相当プログラム | `hdl/tb/` |
| 論理合成・面積見積り | Yosys + `scripts/tr1um.genlib`, `scripts/area_estimate.py` | `scripts/` |
| セル回路検証 | ngspice + `libs.tech/spice/models/ip62_models` | `layout/` |
| スイッチレベル | IRSIM（`.sim`/`.prm`/`.cmd`） | `irsim/` |
| 物理検証 | KLayout DRC/LVS（PDK 付属ランセット） | CI (`.github/workflows/check.yml`) |
| 提出 | `src/<top_cell>.gds` + `<top_cell>.cir` | `src/` |

参照実装（**いずれも CC BY-NC-SA。NC条項に注意**）:
OpenCores `mcs-4`（Reece Pollack）、丸山氏 `MCS4_SYSTEM`。

## 5. 自作が必要なセル一覧（`lef/`）

TR-1um STDLIB（38セル）に対する不足分。回路は `05_cell_circuits.md`。

| セル | 構成 | Tr | 想定面積 | 用途 |
|---|---|---|---|---|
| `DLATCH` | TG型（TG×2 + INV×2 + ローカルCKB） | 8–10T | ~1,800 µm² | ICG、汎用 |
| `DFF` | TG マスタスレーブ | 16T | ~3,500 µm² | 素の FF（DFFR 34T の 56 %） |
| `DFFE` | TG + 帰還保持TG（EN内蔵） | 22T | ~4,900 µm² | イネーブル付き FF |
| `ICG` | ラッチ + AND | 12T | ~2,600 µm² | 4bit 単位クロックゲート |
| `RFCELL` | ラッチ型 10T（または 8T） | 8–10T | ~1,100 µm²/bit | レジスタ/スタックアレイ |
| `GIO` | NAND+NOR プリドライバ + 出力段 + 入力段 | ~16T + 大W | — | D0–D3 双方向 |
| `TIE0` / `TIE1` | 1T | 1T | — | 固定値 |

> **`GIO` は TR-1um / IP62 PDK に存在しない**（PDK にあるのは
> `OSS_ESD_5V_ANA` / `OSS_ESD_5V_VDD` / `OSS_ESD_5V_VSS` と `PAD` のみ）。自作前提。

### イネーブル方式の比較（4bit あたり）

| 方式 | Tr | 面積 |
|---|---|---|
| DFFR + MUX2（合成そのまま） | 196 | 40,740 µm² |
| TG-DFFE ×4 | 88 | 19,400 µm² |
| **ICG 1個 + TG-DFF ×4** | 76 | **16,700 µm²** |

ICG は必ず「EN をラッチしてから AND」構成にしてグリッチを防ぐこと。

### 最小サイズ版ライブラリ（効果大）

既存 STDLIB は全セル **PMOS W=10.2 µm / NMOS W=3.4 µm**（3:1）で、
750 kHz には過剰。**W(P)=5.1 µm** に落とすと行高 62.6 → 約 42 µm、
面積は全体で **約 0.68 倍**。C4004 で使う
INV / NAND2 / NOR2 / AND2 / OR2 / XOR2 / MUX2 / DFF / DFFE だけでも作る価値がある。

## 6. LEF / Liberty（`lef/`）

TR-1um PDK には **LEF も Liberty も無い**。自動 P&R を使うなら整備する。

| ファイル | 内容 |
|---|---|
| `tr1um_tech.lef` | レイヤ / ルーティンググリッド（M1 pitch 3.2 µm, M2 pitch 5.0 µm） |
| `tr1um_stdcell.lef` | セル abstract（行高 62.6 µm。最小サイズ版は別ライブラリ） |
| `tr1um_stdcell.lib` | ngspice 特性化から生成する Liberty |
| `scripts/tr1um.genlib` | Yosys/ABC 用の簡易 genlib（面積のみ、見積り用）※作成済 |

既存 STDLIB のセル面積（GDS 実測 / 行高 62.6 µm）:

```
INV_X1 NAND2 NOR2 BUF_X1        29.1 x 62.6 = 1821.7   (INV=2T, NAND2/NOR2=4T)
NAND3 NOR3 AND2 OR2 BUF_X2      34.6 x 62.6 = 2166.0
NAND4 NOR4 AND3 OR3 INV_X4      40.1 x 62.6 = 2510.3
AND4 OR4 XOR2 XNOR2 BUF_X4      45.6 x 62.6 = 2854.6   (XOR2=10T)
MUX2 BUF_X8                     62.1 x 62.6 = 3887.5   (15T)
DFFR DFFS                      100.6 x 62.6 = 6297.6   (34T)
CLKBUF_X1 DEL1                  51.1 x 62.6 = 3198.9
```
実効密度 ≒ 220 µm²/Tr。

## 7. 面積の見通し（core = 1,840 × 1,840 µm = 3.386 mm²）

| ステップ | 素セル面積 | 配置率60% | 判定 |
|---|---|---|---|
| 既存 STDLIB そのまま | 3.798 mm² | 6.330 | ✕ |
| + レジスタ/スタックをカスタムアレイ化 | 2.900 mm² | 4.834 | ✕ |
| + 残り FF を TG-DFFE(22T) 化 | 2.267 mm² | 3.778 | △（70%でOK） |
| + 最小サイズセル化（×0.68） | **1.619 mm²** | **2.699** | **○** |

効果の大きい順:
① レジスタアレイのカスタム化 **−0.90 mm²**
② DFFE のカスタム化 **−0.63 mm²**
③ セルの最小サイズ化 **−0.65 mm²**

## 8. 次のアクション

1. `hdl/rtl/` に単相・ブラックボックス分離版の `c4004` RTL を起こす
2. `DLATCH` / `DFF` / `DFFE` / `ICG` / `RFCELL` / `GIO` を xschem + ngspice で回路検証
3. 上記セルのレイアウトを描いて KLayout DRC/LVS を通し、実面積を確定
4. 確定面積で `scripts/area_estimate.py` の原単位を更新し、フロアプランを決める
5. `lef/` に LEF/Liberty を整備（自動 P&R を使う場合）
