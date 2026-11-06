# 最小構成 CMOS セル回路集（C4004 用）

前提の変更（2026-09-08）
- **クロックは単相（1相）**。φ1/φ2 の2相クロックは廃止。
- **3ステートは GIO（双方向 I/O セル）でのみ使用**。内部バスは3ステートを使わずMUX化。
- **レジスタファイル + PC/スタックはスクラッチ（カスタムアレイ）で作る**。

## 0. TR-1um の面積原単位（実測から導出）

`STDLIB/LogicCells` の GDS 面積とネットリスト実測トランジスタ数から:

| セル | 面積 µm² | Tr数 | µm²/Tr |
|---|---|---|---|
| INV_X1 | 1,821.7 | 2 | 910.9 |
| NAND2 / NOR2 | 1,821.7 | 4 | 455.4 |
| AND2_X1 | 2,166.0 | 6 | 361.0 |
| XOR2 | 2,854.6 | 10 | 285.5 |
| MUX2 | 3,887.5 | 15 | 259.2 |
| **DFFR / DFFS** | 6,297.6 | **34** | **185.2** |

- 全セル PMOS **W=10.2 µm** / NMOS **W=3.4 µm**、L=1.0 µm、行高 62.6 µm。
- 多トランジスタセルの実効密度 **≒ 220 µm²/Tr**。以下の見積りはこれを使う。
- **750 kHz 動作では PMOS W=10.2 µm は過剰**。W(P)=5.1 µm 程度まで落とせば
  行高 62.6 → 約 42 µm となり、全体で **約 0.68 倍**が狙える。

---

## 1. 単相クロック化の方針

### 1.1 何が変わるか

| | 2相（オリジナル4004） | 単相（C4004） |
|---|---|---|
| クロック入力ピン | φ1, φ2（2本） | CLK（1本）→ **パッド1本空く** |
| 内部ステート | φ1/φ2 で 8ステート生成 | CLK 同期の3bitカウンタで A1..X3 |
| 記憶素子 | ダイナミック2相ラッチ | 単相エッジトリガ FF / ゲーテッドラッチ |
| リスク | φ1/φ2 のオーバーラップ | CLK / CLKB のスキュー（セル内部で吸収） |

ピン割当（16パッド = 信号14 + VDD + VSS）:
`D0-D3(GIO) / SYNC / CM-ROM / CM-RAM0-3 / TEST / RESET / CLK` = 13本 → **1本空き**
（空きは `CLKOUT`、スキャン用 `SI/SO`、または `PHI_OUT` などデバッグに割り当て可）

### 1.2 単相での注意

- TG 型 FF は内部で CLK/CLKB を作るので、**セル内部にクロックインバータを持たせる**
  （現行 DFFR も同じ構成）。外部は真の単相。
- ホールド時間違反を避けるため、**クロックインバータはセルローカル**に置き、
  グローバルに CLKB を配らない。
- 全ラッチを使う場合は、**内部で非オーバーラップ2相を生成**する方式もあるが、
  今回は「単相エッジトリガ FF + イネーブル」を基本とする。

---

## 2. DLATCH — 最小構成 CMOS

### 2.1 TG 型 D ラッチ（静的・8T）★推奨

```
            G                    GB
        ┌───┤├───┐           ┌───┤├───┐
  D ────┤  TG1   ├──● Q_int ──┤  TG2   ├──┐
        └───┤├───┘  │        └───┤├───┘  │
            GB      │            G       │
                    │                    │
                   ┌┴┐INV1              ┌┴┐INV2
                   └┬┘                  └┬┘
                    ●───────── Q          │
                    └─────────────────────┘   (帰還ループ)
```

- 構成: TG1(2T) + TG2(2T) + INV1(2T) + INV2(2T) = **8T**
  （+ G から GB を作るローカルインバータ 2T = 実質 **10T**）
- G=1 でスルー、G=0 で保持。完全静的。
- TR-1um 面積見積り: 8T × 220 = **約 1,800 µm²**（現 DFFR の 29 %）
- 注意: TG は NMOS/PMOS 対で作ること（NMOS 単独パスゲートだと
  Vth 落ちで High が 5−0.76 = 4.24 V になり、次段 PMOS が完全に切れない）

### 2.2 クロックドインバータ（C²MOS）型 D ラッチ（静的・10T）

```
        G ┐                      GB ┐
  D ──►[ clocked INV ]──● Q_int ──►[ INV ]── Q
                        │
                        └──◄[ clocked INV (帰還) ]──
```
- 構成: clocked INV(4T) + INV(2T) + 帰還 clocked INV(4T) = **10T**
- TG 型よりクロック負荷が大きいが、入力とクロックの分離が良く
  レイアウトが直線的（配列に組みやすい）。
- 面積見積り: **約 2,200 µm²**

### 2.3 ダイナミック（非推奨だが最小・3〜5T）

```
        G
  D ──┤├── ● ──┤>o── Q        (NMOS パスゲート 1T + INV 2T = 3T)
             Cs
```
- **3T**（NMOSのみ）または **5T**（TG 化）。保持はノード容量まかせ。
- 1 µm/5 V ではリーク小のため 750 kHz なら理屈上は成立するが、
  **最低動作周波数の下限が発生**し、テスト・デバッグが難しくなるので
  C4004 では採用しない（オリジナル 4004 はこの方式）。

---

## 3. DFFE — 最小構成 CMOS（イネーブル付き D-FF）

### 3.1 現状の問題

TR-1um STDLIB には DFFE が無い → 合成すると **DFFR(34T) + MUX2(15T) = 49T /
10,185 µm²** になる。C4004 では FF が 231 本あり、ここだけで **2.3 mm²**。

### 3.2 TG マスタスレーブ DFF（静的・16T）

```
  ┌──────── master ────────┐  ┌──────── slave ─────────┐
        CKB                       CK
  D ───┤ TG ├──●──┤>o──●──────┤ TG ├──●──┤>o──● Q
        CK    │        │       CKB    │       │
              │  ┌──┐  │              │  ┌──┐ │
              └──┤<o├──┘              └──┤<o├─┘
                 └──┘ (弱帰還INV)        └──┘
```
- TG(2T)×2 + INV(2T)×2 + 帰還INV(2T)×2 = **12T** + CK/CKB インバータ 2T = **14〜16T**
- Southampton 講義資料でも TG 実装 16T / トライステート実装 20T とされる。
- 面積見積り: **約 3,500 µm²**（DFFR 6,297.6 µm² の 56 %）

### 3.3 TG-DFFE（帰還 MUX 内蔵・22T）★推奨

イネーブルは「マスタラッチの帰還経路を切り替える」形で内蔵する。
外付け MUX2 を置くより 27T ぶん小さい。

```
              EN・CKB
  D ─────────┤  TG_D  ├──●──┤>o──●───┤ TG_S ├──●──┤>o──● Q
                          │       │    (CK)     │       │
             /EN・CKB     │  ┌──┐ │             │  ┌──┐ │
       ┌────┤  TG_H  ├────┘  │<o│ │             └──┤<o├─┘
       │      (保持)          └─┬┘ │                └──┘
       └───────────────────────┴──┘
```
- TG_D / TG_H を `EN` と `CK` の AND で開閉（内部に NAND2+INV = 6T の制御ロジック）
- 概算: TG×3(6T) + INV×4(8T) + 制御 NAND/INV(6T) + CK バッファ(2T) = **約 22T**
- 面積見積り: **約 4,900 µm²**（現 DFFR+MUX2 の **48 %**）

### 3.4 ローカルクロックゲーティング（4bit まとめて効く）

4bit レジスタ単位でイネーブルが共通なら、
**ラッチベースのクロックゲータ（ICG: latch + AND ≒ 12T）を 1 個**置いて
その先は素の DFF(16T) にしたほうが小さい。

| 方式 | 4bit あたり Tr | 面積 µm² |
|---|---|---|
| DFFR + MUX2（現状） | 4 × 49 = 196 | 40,740 |
| TG-DFFE ×4 | 4 × 22 = 88 | 19,400 |
| **ICG 1個 + TG-DFF ×4** | 12 + 4×16 = 76 | **16,700** |

→ **C4004 では 4bit 単位でイネーブルが揃うので ICG 方式が最有利。**
ただしクロックゲーティングはグリッチ耐性が必要なので、
ICG は必ず「ラッチ＋AND」構成（EN をラッチしてから AND）にすること。

### 3.5 TSPC（True Single Phase Clock, 動的・9〜11T）

単相クロックという条件には最も合致し、最小 **9T**。
ただし内部ノードが動的で、低速動作（750 kHz）ではリークによる誤動作リスクがある。
**C4004 の本命では使わないが、TEG（テスト構造）として1個入れて評価する価値はある。**

---

## 4. レジスタファイル / PC スタック — カスタムアレイ

### 4.1 対象と規模

| ブロック | 構成 | ビット数 |
|---|---|---|
| Scratchpad（インデックスレジスタ） | 16 word × 4 bit | 64 |
| PC + スタック | 4 level × 12 bit | 48 |
| **合計** | | **112 bit** |

DFFE で作ると 112 × 10,185 = **1.14 mm²**。カスタムアレイなら **0.1 mm² 程度**。

### 4.2 候補セル

#### (a) 6T SRAM セル（最小・6T）

```
        WL                                     WL
         │                                      │
   BL ──┤├──●──────┬──────●──┤├── BLB
             │  ┌──┴──┐   │
             │  │ INV │   │      2つのインバータをたすき掛け
             └──┤ INV │───┘
                └─────┘
```
- **6T**。最小面積。ただし
  - 読み出しに **プリチャージ + 差動センス**が要る
  - **セルレシオ設計**（読み出し破壊しない β 比）が必須
  - 1 µm・W(N)min=3.4 µm の DR では比の作り込みがやりにくい
- 面積見積り: 6T × 110 µm²/Tr（アレイ内密度）= **約 660 µm²/bit**

#### (b) 8T セル（6T + 単一終端リードポート）★バランス良

```
   [6T セル] ── Q ──┤ N1 ├──┐
                            ├── RBL   (RWL で N2 をON)
             RWL ──┤ N2 ├───┘
```
- **8T**。リードポートが分離され**リードディスターブが無い**、
  センスアンプ不要（単一終端、インバータで受けるだけ）。
- ライト用に BL/BLB とライトドライバは必要。
- 面積見積り: **約 880 µm²/bit** → 112 bit = **98,600 µm² = 0.10 mm²**

#### (c) ラッチ型セル（10T）★第一シリコン推奨

```
        WWL                                RWL
         │                                  │
  WD ──┤TG├──●──┤>o──●──┤>o──● Q ──┤TG├── RD
              │           │
              └───────────┘   (2インバータ ループ)
```
- 構成: ライトTG(2T) + INV(2T) + INV(2T) + 帰還INV(2T) + リードTG(2T) = **10T**
- **プリチャージもセンスも比設計も不要**。ただ大きい。
- 完全静的でスキャン・観測が容易 → **初回シリコンで最も安全**。
- 面積見積り: **約 1,100 µm²/bit** → 112 bit = **123,000 µm² = 0.12 mm²**

#### (d) 比較

| セル | Tr | µm²/bit | 112bit 合計 | センス | 比設計 | 推奨度 |
|---|---|---|---|---|---|---|
| 6T SRAM | 6 | ~660 | 0.074 mm² | 要 | 要 | △ |
| 8T | 8 | ~880 | 0.099 mm² | 不要 | 緩い | ○ |
| **ラッチ型 10T** | 10 | ~1,100 | **0.123 mm²** | 不要 | 不要 | **◎** |
| DFFE（現状） | 49 | 10,185 | 1.141 mm² | — | — | ✕ |

+ デコーダ / ワードラインドライバ / ライトドライバ で **約 0.10〜0.12 mm²** を別途見込む。

### 4.3 PC / スタック特有の事情

- スタックは **3段（+PC = 4エントリ）× 12 bit**。ポインタ 2 bit の
  リングカウンタでワードを選ぶ**ラウンドロビン**方式が最小
  （4004 オリジナルと同じ。真のシフトスタックにするとシフト経路が増える）。
- PC は毎サイクル +1 する → **12bit インクリメンタを1個**、
  アレイの外に置いて read → +1 → write back する。
  （アレイ内に加算器を分散させない）
- Scratchpad は 16 word × 4 bit の 1R/1W。4004 は「read → ALU → write」なので
  **1ポート（read/write 時分割）でも足りる**。→ セル (c) の RWL/WWL を共通化すれば **8T** に落とせる。

---

## 5. GIO（双方向 I/O セル）

> **注意: `GIO` という名前のセルは TR-1um / IP62 PDK には含まれていない**
> （PDK にあるのは ESD 素子 `OSS_ESD_5V_ANA` と `PAD` のみ）。
> 以下は自作する場合の標準的な最小構成。

```
                                   ┌──── VDD
                                 ──┤ MP  (W大)
   DOUT ──┐                        │
          ├─[ pre-driver ]─────────●──────●─────► PAD ──[ESD]──[bond]
   OEN  ──┘                        │      │
                                 ──┤ MN   │
                                   └──── GND
                                          │
   DIN  ◄──────────[ INV / シュミット ]────┘
```

- **出力段（3ステート）**: `OEN=0` のとき MP/MN とも OFF（Hi-Z）。
  プリドライバは NAND(4T) + NOR(4T) を使うのが定番:
  - `PG = NAND(DOUT, OEN)` → MP のゲート
  - `NG = NOR(!DOUT, !OEN)` → MN のゲート
  - MP/MN を独立に制御できるので Hi-Z が確実に作れる。
- **入力段**: インバータ2段（4T）。ノイズ耐性が要るならシュミット（6T）。
- **合計**: プリドライバ 8T + 出力段 2T + 入力段 4T + OEN インバータ 2T ≒ **16T**
  （+ 出力トランジスタは W を大きく取る: パッド駆動なら W(N) ≥ 100 µm 級）
- **必須の付帯事項**
  - パッドからの ESD は `OSS_ESD_5V_ANA` を使う（フレームに実装済み）
  - MP のバックゲートは VDD、MN は GND に確実にタイダウン
  - Hi-Z 時にフローティングしないよう、**バスホルダ（弱いたすき掛けインバータ 4T）**を
    入れるか、外部プルアップ前提とするかを決める
  - D0–D3 は 4 個必要 → GIO ×4

---

## 6. 面積再見積り（本方針適用後）

| ステップ | 素セル面積 | 配置率60% | 配置率70% | 判定(core 3.386 mm²) |
|---|---|---|---|---|
| 現状（既存 STDLIB そのまま） | 3.798 mm² | 6.330 | 5.425 | ✕ |
| + レジスタ/スタックをカスタムアレイ化 | 2.900 mm² | 4.834 | 4.143 | ✕ |
| + 残り FF を TG-DFFE(22T) 化 | 2.267 mm² | 3.778 | **3.238** | ○(70%) |
| + 最小サイズ・カスタムセル（×0.68） | **1.619 mm²** | **2.699** | 2.313 | **◎** |

> **結論: 単相クロック + カスタムレジスタアレイ + 最小サイズ TG 系セルで
> TR-1um 2.5×2.5 mm に収まる見通しが立つ。**
> 最も効くのは順に ①レジスタアレイのカスタム化（−0.90 mm²）
> ②DFFE のカスタム化（−0.63 mm²）③セルの最小サイズ化（−0.65 mm²）。

---

## 出典

- [Latches and Flip-Flops (Univ. of Southampton, icd09.pdf)](https://www.southampton.ac.uk/~bim/notes/icd/lecture/pdf/icd09.pdf)
  — TG ラッチ / トライステートラッチ / マスタスレーブ FF のトランジスタ数
- [CMOS D-type transmission-gate latch (Univ. Hamburg HADES)](https://tams-www.informatik.uni-hamburg.de/applets/hades/webdemos/05-switched/40-cmos/latch_print.html)
- [VLSI Design — Sequential MOS Logic Circuits (TutorialsPoint)](https://www.tutorialspoint.com/vlsi_design/vlsi_design_sequential_mos_logic_circuits.htm)
- [A Modified Implementation of Tristate Inverter Based Static Master-Slave Flip-Flop (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3958701/)
- [E-TSPC: Extended True Single-Phase-Clock CMOS circuit technique (Springer)](https://link.springer.com/chapter/10.1007/978-0-387-35311-1_14)
- [ECE410 Lecture Notes 11 — Layout of Multiple Cells (Michigan State Univ.)](https://www.egr.msu.edu/classes/ece410/mason/files/Ch11.pdf)
- [Lab 6 Supplement: Guide to Designing CMOS Flip Flops (MSU)](https://www.egr.msu.edu/classes/ece410/mason/files/lab6-supplement.pdf)
- [Design and Simulation of 6T SRAM Array (arXiv 2508.09419)](https://arxiv.org/html/2508.09419v1)
- [7T/8T register file (UT Austin, 7_8T_TVLSI.pdf)](https://sites.utexas.edu/CRL/files/2018/11/7_8T_TVLSI.pdf)
- [The 8-Bit, 32 Word Register File (CMOSedu / EE421L)](https://cmosedu.com/jbaker/courses/ee421L/f21/students/wolak/proj/proj.html)
- [US5300835A — CMOS low power mixed voltage bidirectional I/O buffer](https://patents.google.com/patent/US5300835A/en)
- [US5808492A — CMOS bidirectional buffer](https://patents.google.com/patent/US5808492)
- TR-1um PDK 実測: `STDLIB/LogicCells/{gds,extracted}`, `libs.tech/klayout/libraries/TR-1um_frame_25x25.gds`
