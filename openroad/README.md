# `openroad/` — OpenROAD & Yosys 設定ファイル・LEF・スクリプト一覧

本ディレクトリには、OpenSUSI TR-1um（1 µm CMOS、2層金属配線 `M1`/`M2`）プロセスにおいて `c4004_core`（624標準セル＋`SRAM128` マクロ、全657信号ネット）を DRC エラーおよびセル内ショートなしで自動配置配線するための **OpenROAD 設定ファイル（LEF、Tcl スクリプト、配置辞書、ルーティングガイド、DEF）** および **Yosys 論理合成設定ファイル** がまとめられています。

---

## 1. ファイル一覧 (File Inventory)

### 1.1 Yosys 論理合成 & ゲートレベルネットリスト

| ファイル名 | 説明 |
| :--- | :--- |
| [`synth.ys`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/synth.ys) | Yosys 論理合成スクリプト。`rtl/c4004_core.v` を読み込み、TR-1um 標準セル (`tr1um_typ_5v0_25c.lib`) と `SRAM128.lib` にマッピングし、`TIEH`/`TIEL` および出力バッファ `BUF_X1` を挿入します。 |
| [`abc.constr`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/abc.constr) | Yosys ABC マッピング用の駆動セル (`BUF_X2`)・負荷容量 (`0.562 pF`) 制約ファイル。 |
| [`c4004_core_buffered_or.v`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/c4004_core_buffered_or.v) | `synth.ys` の出力に [`scripts/insert_high_fo_buffers.py`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/scripts/insert_high_fo_buffers.py) で初段シュミットトリガ `BUFTH`（7個）、行別クロック/リセットツリー、および高ファンアウト分割バッファ (`BUF_X2`) を挿入した OpenROAD 入力用ネットリスト（624標準セル＋`SRAM128` 1個）。 |

### 1.2 OpenROAD 用テクノロジ・セル・マクロ LEF ファイル

| ファイル名 | 説明 |
| :--- | :--- |
| [`TR-1um_tech_or.lef`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/TR-1um_tech_or.lef) | OpenROAD 用テクノロジ LEF。サイト `TR1UM` (`5.4 µm × 59.4 µm`)、水平配線層 `METAL1` (幅 `2.6 µm`, 最小スペース `2.2 µm`, ピッチ `5.4 µm`)、層間ビア `VIA1` (`3.4 × 3.4 µm`, カット `1.8 × 1.8 µm`)、垂直配線層 `METAL2` (幅 `2.6 µm`, 最小スペース `2.4 µm`, ピッチ `5.4 µm`) を定義。 |
| [`TR-1um_cells_or.lef`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/TR-1um_cells_or.lef) | PDK の `TR-1um_cells.lef` の多角形 (`POLYGON`) を水平矩形 (`RECT`) に分解し、DFF 内部ノード (`CKB/CKP/QM/QS`) を `OBS` に移動したクリーンな標準セル LEF。 |
| [`TR-1um_cells_grt_fullobs.lef`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/TR-1um_cells_grt_fullobs.lef) | **Global Route (`run_grt.tcl`) 用標準セル LEF**。セル内部の `METAL1` (`y = 1.1..58.3 µm`) を全面 `OBS` とし、Global Router が標準セル行の内部を水平 `M1` トランクとして使用しないよう誘導します。 |
| [`TR-1um_cells_m2only.lef`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/TR-1um_cells_m2only.lef) | **Detailed Route (`run_drt.tcl`) 用標準セル LEF**。セル内部の `METAL1` を全面 `OBS` にすると同時に、全標準セルの信号ピンを `LAYER METAL2` パッドのみに限定しています。これにより TritonRoute は必ず垂直 `M2` でセルピンにアクセスし、隣接ピンやセル内 `M1` 配線とのショートを物理的にゼロにします。 |
| [`SRAM128_or.lef`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/SRAM128_or.lef) | `32×4-bit` SRAM ハードマクロ (`1166.1 × 185.6 µm`) の OpenROAD 用 LEF。内部の `M1`/`M2` 領域を適切に `OBS` 保護し、下辺の信号ピン (`A[4:0]`, `D[3:0]`, `Q[3:0]`, `CE`, `WE`) と左右両端の `VDD`/`VSS` ピンを定義。 |

### 1.3 OpenROAD 実行 Tcl スクリプト・配置辞書・ガイド・DEF

| ファイル名 | 説明 |
| :--- | :--- |
| [`run_grt.tcl`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/run_grt.tcl) | **OpenROAD フロアプラン・配置・Global Route 実行スクリプト** (`openroad -exit openroad/run_grt.tcl`)。コア初期化 (`1840 × 1840 µm`)、`SRAM128` 配置 (`334.8, 1596.0 µm`)、4辺19ピン配置、9本のアクティブ行生成、`tap2_exact_pos.tcl` による3分割セル配置、`M1` 行内 OBS + `M2` `TAP2` 縦列 OBS 設定、および `global_route` を実行します。 |
| [`run_drt.tcl`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/run_drt.tcl) | **OpenROAD Detailed Route 実行スクリプト** (`openroad -exit openroad/run_drt.tcl`)。`TR-1um_cells_m2only.lef`、`placed_tap2.def`、およびチャネルスナップ済みガイド `route_tap2_strict.guide` を読み込み、TritonRoute (`detailed_route`) で全ネットを詳細配線して `routed_tap2.def` を出力します。 |
| [`tap2_exact_pos.tcl`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/tap2_exact_pos.tcl) | 4列の `TAP2` (`x = 21.6, 615.6, 1215.0, 1809.0 µm`) によって横3セグメント (`108, 109, 108` サイト) に分割され、かつ空きサイトが2〜3サイト塊（`FILL2`/`FILL3` サイズ）になるよう最適化された全624標準セルの座標辞書 (`exact_tap2_pos`)。 |
| [`placed_test4edge_1v.def`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/placed_test4edge_1v.def) | `TAP2` 3分割パッキング前の初期9行配置 DEF（`scripts/run_tap2_flow.py` の入力）。 |
| [`placed_tap2.def`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/placed_tap2.def) | `run_grt.tcl` が出力した、`TAP2` 3分割配置済みの DEF（全行 `N` 向きに統一）。 |
| [`route_tap2.guide`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/route_tap2.guide) | `run_grt.tcl` (`global_route`) が出力した初期グローバルルーティングガイド。 |
| [`route_tap2_strict.guide`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/route_tap2_strict.guide) | `route_tap2.guide` を `81.0 µm` チャネルグリッドにスナップし、`run_drt.tcl` に入力するための詳細配線ガイド。 |
| [`routed_tap2.def`](file:///Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/routed_tap2.def) | `run_drt.tcl` (`detailed_route`) が出力した詳細配線完了 DEF（この後 `scripts/reterminate_tap2_nets.py` で4辺パッド座標へピン再終端を行い、`apr/c4004_core_4edge_routed.def` となります）。 |

---

## 2. 2層配線 (`M1`/`M2`) × `TAP2` 3分割の OpenROAD 設計手法

TR-1um プロセスは配線層が `METAL1`（水平優先）と `METAL2`（垂直優先）の **2層のみ** であり、標準セル内部のトランジスタ間結線に `METAL1` が全面的に使用されています。そのため、一般的な3層以上のプロセスと同じ設定で OpenROAD を走らせると、標準セルの上を横切る `METAL1` 配線とセル内部の `METAL1` が無数にショートします。

本設計では、以下の4つの工夫を組み合わせることで OpenROAD による 100% 自動配線を達成しています。

1. **1行配置・2行空けの水平配線チャネル構造（9アクティブ行）**
   - 標準セル行（高さ `59.4 µm`）を3行ごとに1行だけ残し（`y = 59.4, 237.6, 415.8, 594.0, 772.2, 950.4, 1128.6, 1306.8, 1485.0 µm` の計9行）、各行の間に **2行分（`118.8 µm` = 水平 `M1` トラック22本分）の配線専用チャネル** を確保しています。
2. **`M2` 限定ピンアクセス (`TR-1um_cells_m2only.lef`) + 行内 `M1` オブストラクション**
   - 標準セルのピン形状を `METAL2` のみに限定し、さらに各標準セル行の内部 (`yMin + 1.1 µm` 〜 `yMax - 1.1 µm`) に `odb::dbObstruction_create` で `METAL1` の配線禁止領域を設定しています。
   - これにより、標準セルへの出し入れはすべて **垂直 `METAL2`** で行われ、**水平 `METAL1` 幹線はすべて行間の `118.8 µm` チャネル内** に収まります。
3. **`TAP2` 縦4列によるコア3分割と `M2` 電源ストラップ保護**
   - 各行の左端 (`x = 21.6 µm`)、中1 (`x = 615.6 µm`)、中2 (`x = 1215.0 µm`)、右端 (`x = 1809.0 µm`) の4箇所に2サイト幅 (`10.8 µm`) の `TAP2` セル用の空白を空け、標準セルを3セグメント (`108, 109, 108` サイト) に配置しています。
   - OpenROAD 実行時には、この4列の `TAP2` 領域 (`x + 1.0 µm` 〜 `x + 9.8 µm`) に **`METAL2` オブストラクション** を設定することで、後から KLayout で敷設する縦方向の `M2` `VDD`/`VSS` 電源ストラップと信号 `M2` 配線が衝突しないようにしています。
4. **`FILL3` / `FILL2` デキャップ充填を見越したセル間隔の量子化**
   - `tap2_exact_pos.tcl` を生成する際、各セグメント内の空きサイトを1サイトずつバラバラに分散させるのではなく、**3サイト塊 (`FILL3`)** または **2サイト塊 (`FILL2`)** になるようにギャップ長を量子化して配置しています。これにより、KLayout でのフィラー挿入時に1サイト幅の隙間を全コアでわずか3箇所 (`FILL1`×3) に抑え、42個のアクティブ MOS デキャップ (`FILL3`×29, `FILL2`×13) を高密度に充填できています。

---

## 3. スタンドアロン実行手順 (How to Run)

リポジトリルート (`/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004`) から以下のコマンドで各ステップを実行できます。

```bash
# 1. Yosys 論理合成 (c4004_core.v -> syn/c4004_core_raw.v)
yosys -s openroad/synth.ys

# 2. OpenROAD Global Route (placed_tap2.def, route_tap2.guide 生成)
openroad -exit openroad/run_grt.tcl

# 3. OpenROAD Detailed Route (routed_tap2.def 生成)
openroad -exit openroad/run_drt.tcl

# (一括実行する場合は scripts/run_tap2_flow.py を使用)
python3 scripts/run_tap2_flow.py
```
