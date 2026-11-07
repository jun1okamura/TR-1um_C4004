# C4004 設計方針と物理実装仕様

初版策定: 2026-09-08 / 最終実装更新: 2026-11-06  
根拠: [`03_TR-1um_facts.md`](03_TR-1um_facts.md)（PDK・ライブラリ実測）/ [`04_area_estimation.md`](04_area_estimation.md)（面積見積り）/ [`05_cell_circuits.md`](05_cell_circuits.md)（回路）/ [`07_sram6t_macro.md`](07_sram6t_macro.md)（SRAM128 マクロ）。

---

## 1. 確定した基本設計方針

| # | 方針 | 理由・最終実装形態 |
|---|---|---|
| 1 | **クロックは単相 (`clk`)** | φ1/φ2 の2相クロックを廃止し、単相 `clk` 同期の8フェーズ (`A1..X3`) 構成を採用。空いた1ピン (`P9`) を外部トランシーバ方向制御 `d_oe` に割当 |
| 2 | **3ステートは `OSS_FRAME_GIO` (`OSS_ESD_5V_DIO`) のみ** | コア内部は `d_out[3:0] / d_oe / d_hiz / d_in[3:0]` に完全分離し、パッドリング内の `OSS_ESD_5V_DIO` で双方向バス `D[3:0]` を駆動 |
| 3 | **レジスタファイル + スタックは `SRAM128`（6T 128bit SRAM）に統合** | インデックスレジスタ `R0..R15` (64 bit) とサブルーチン戻り番地スタック (36 bit) を単一ハードマクロ [`module/SRAM128`](../module/SRAM128/) (`0.2164 mm²`) に格納し、標準セル FF を **40個** に削減 |
| 4 | **全外部入力ピン初段にシュミットトリガ `BUFTH` 挿入** | 外部パッドからの入力7本 (`clk, rst, test, d_in[3:0]`) はすべて初段で `BUFTH` を通し、さらに `clk`/`rst_n` は9行別の `BUF_X2` ツリー (`FO <= 10`) で分配 |
| 5 | **2層配線 (`M1`/`M2`) チャネル P&R + `TAP2` 3分割 + `FILL3/2` 充填** | 9本のアクティブ行間に2行幅 (`118.8 µm`) の水平 `M1` チャネルを設け、セルピンは垂直 `M2` のみでアクセス。縦4列の `TAP2` でコアを横3分割し、空き領域に MOS デキャップ `FILL3`/`FILL2` を充填 |

---

## 2. ピン割当（`OSS_FRAME` 16パッド = 信号14 + VDD + VSS、全正論理）

| パッド番号 | 辺 | 信号名 | 方向 | パッドセル | コア接続・備考 |
| :-: | :-: | :--- | :-: | :--- | :--- |
| **P1** | 北 (Top) | `clk` | in | `OSS_ESD_5V_DIO` | 単相システムクロック入力（初段 `BUFTH`） |
| **P2** | 北 (Top) | `sync` | out | `OSS_ESD_5V_DIO` | `X3` フェーズ同期パルス出力（正論理 High アクティブ） |
| **P3 〜 P6** | 西 (Left) | `D[3:0]` | inout | `OSS_ESD_5V_DIO` | 4-bit 双方向データバス (`P3=D[3], P4=D[2], P5=D[1], P6=D[0]`) |
| **P7** | 南 (Bottom) | `rst` | in | `OSS_ESD_5V_DIO` | リセット入力（正論理 High アクティブ、初段 `BUFTH`） |
| **P8** | 南 (Bottom) | `VSS` | power | `OSS_ESD_5V_VSS` | グラウンド (`0.0 V`) — 4辺 `M2` `VSS` リングおよび `TAP2` に直結 |
| **P9** | 南 (Bottom) | `d_oe` | out | `OSS_ESD_5V_DIO` | データバス出力イネーブルモニタ (`d_oe = ~d_hiz`、外部 `74LVC8T245` 等制御用) |
| **P10** | 南 (Bottom) | `test` | in | `OSS_ESD_5V_DIO` | `JCN` 命令用外部テスト条件入力（初段 `BUFTH`） |
| **P11 〜 P14** | 東 (Right) | `cm_ram[0:3]` | out | `OSS_ESD_5V_DIO` | RAM バンク選択出力 (`P11=cm_ram[0] .. P14=cm_ram[3]`) |
| **P15** | 北 (Top) | `cm_rom` | out | `OSS_ESD_5V_DIO` | ROM バンク選択ストローブ出力 |
| **P16** | 北 (Top) | `VDD` | power | `OSS_ESD_5V_VDD` | 電源 (`5.0 V`) — 左右両端 `TAP2`・`SRAM128`・全標準セル行に給電 |

---

## 3. RTL 記述ルール（[`rtl/c4004_core.v`](../rtl/c4004_core.v), [`rtl/c4004_top.v`](../rtl/c4004_top.v)）

1. **単相 `posedge clk` 同期**:
   - 8フェーズ `A1, A2, A3, M1, M2, X1, X2, X3` は 3-bit ステートカウンタ `state[2:0]`（リセット時 `3'd7 = X3`、`DFFS`×3）で生成。
2. **双方向バスの分離**:
   - `inout [3:0] D` はトップラッパ `c4004_top` のみで扱い、`c4004_core` は `d_in[3:0]`, `d_out[3:0]`, `d_oe`, `d_hiz` の単方向ポートを持つ。
3. **`SRAM128` 1ステート1アクセス（クロック後半 `clk = 0` アクセス）**:
   - `clk = 1` の前半期間に `CE = 0` でビット線をプリチャージしつつアドレス `sram_a[4:0]`・書込みデータ `sram_di[3:0]` を確定させ、`clk = 0` の後半期間に `sram_ce = (~clk) & rst_n & sram_ce_en` を High にして Read (`WR=0`) または Write (`WR=1`) を実行。
   - アクティブ `pc[11:0]` は FF（12 bit）上に保持し、`SRAM128` にはインデックスレジスタ `R0..R15`（`A[4]=0`）およびサブルーチンスタック（`A[4]=1`）を格納することで、全命令でポート競合ゼロを達成。
4. **`MUXDFFRB` への自動畳み込み**:
   - ホールド機能付き FF（`DFFRB` + `MUX2`）は、`module/STDCELL/` の複合セル `MUXDFFRB`（18サイト、`5,773.7 µm²`）へマージ（40 FF のうち 29 個が `MUXDFFRB`）。

---

## 4. 検証・実装フローとディレクトリ構成

| 段階 | ツール / スクリプト | 配置ディレクトリ |
|---|---|---|
| 1. RTL 機能検証 | `iverilog` + `vvp`（全45/46命令・21チェック項目自己検査） | [`rtl/`](../rtl/) |
| 2. 論理合成 & バッファ挿入 | Yosys ([`openroad/synth.ys`](../openroad/synth.ys)) + [`scripts/insert_high_fo_buffers.py`](../scripts/insert_high_fo_buffers.py) | [`syn/`](../syn/), [`openroad/`](../openroad/README.md) |
| 3. 2層配線 LEF & OpenROAD P&R | [`scripts/make_m2only_lef.py`](../scripts/make_m2only_lef.py), [`scripts/run_tap2_flow.py`](../scripts/run_tap2_flow.py) ([`run_grt.tcl`](../openroad/run_grt.tcl), [`run_drt.tcl`](../openroad/run_drt.tcl)) | [`openroad/`](../openroad/README.md) |
| 4. 4辺パッド整合 & GDSII 構築 | [`scripts/reterminate_tap2_nets.py`](../scripts/reterminate_tap2_nets.py), [`scripts/build_core_and_chip_gds.py`](../scripts/build_core_and_chip_gds.py) | [`apr/`](../apr/) |
| 5. サインオフ DRC / LVS | KLayout + [`scripts/build_lvs_spice.py`](../scripts/build_lvs_spice.py), [`scripts/verify_core_and_chip.py`](../scripts/verify_core_and_chip.py) | [`apr/`](../apr/) |
| 6. Post-Layout `ngspice` 検証 | [`scripts/prep_extracted_ngspice.py`](../scripts/prep_extracted_ngspice.py), [`scripts/run_chip_verif.py`](../scripts/run_chip_verif.py) | [`apr/simulation/`](../apr/simulation/) |
| 7. MPW 提出データ生成 | [`scripts/prepare_mpw_submission.py`](../scripts/prepare_mpw_submission.py) (`tr_1um_jun1okamura.gds`, `.cir`) | [`src/`](../src/), [`info.yaml`](../info.yaml) |

---

## 5. 面積の推移（事前見積り vs 最終実チップ結果）

| ステップ | 素セル＋マクロ面積 | コア面積 (`3.386 mm²`) 比 | 判定・備考 |
|---|---:|---:|---|
| ① 初期見積り（旧 STDLIB そのまま・全FF合成） | `3.798 mm²` | `112.2%` | ✕（配線領域を含めると約2倍超過） |
| ② 事前改善案見積り（6T SRAM + 縮小セル） | `1.619〜1.947 mm²` | `47.8〜57.5%` | ○（収容見通し） |
| **③ 最終実チップ (`c4004_core`: 624論理セル + `SRAM128`)** | **`1.147 mm²`** | **`33.9%`** | **◎（9行×2行幅チャネル＋`TAP2` 4列＋`FILL2/3` 42個込みで 100% DRC/LVS クリーン収容）** |
