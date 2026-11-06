# reference/ — 調査資料

TR-1um プロセスで Intel 4004 互換 CPU（C4004）を実装できるかの事前調査。

| ファイル | 内容 |
|---|---|
| `01_Intel4004_spec.md` | Intel 4004 のスペック・アーキテクチャ・ピン配置・MCS-4ファミリ |
| `02_CMOS_implementations.md` | CMOS/HDL 実装事例（Tiny Tapeout SKY130版、OpenCores mcs-4、4004.com 等） |
| `03_TR-1um_facts.md` | TR-1um(IP62) の実測制約：DR、フレーム/パッド、STDLIB セル面積 |
| `04_area_estimation.md` | Yosys 合成 + 実セル面積による面積見積り（既存STDLIB前提） |
| `05_cell_circuits.md` | **最小構成 CMOS 回路集**: 単相クロック / DLATCH / DFFE / レジスタファイル・スタック / GIO |
| `06_design_policy.md` | **設計方針まとめ**: ピン割当 / RTL記述ルール / 検証フロー / 自作セル一覧 / LEF計画 / 次アクション |
| `07_sram6t_macro.md` | **6T SRAM マクロ構成**: `C4004_SRAM32X4`（32w×4b）/ アドレスマップ / セル設計 / アレイ・周辺 / 内部タイミング / アクセススケジュール / 検証計画 |
| `08_senseamp_refs.md` | **センスアンプ文献集（1 µm 世代）**: 特許8件（無料・全回路図）/ JSSC 論文 / 書籍 / トポロジ比較 / TR-1um 向けオフセット見積りと設計目標 |

## 要旨

- 4004 は 4bit・46命令・16ピン DIP・740–750 kHz。信号14本+電源2本は
  **TR-1um の OSS_FRAME（信号14 + VDD + VSS）と完全一致**。
- CMOS 実装の先行例あり: **Tiny Tapeout ttsky25a #39 "MCS-4 4004 CPU"**（SKY130、
  1タイル ≒ 2,000ゲート、750 kHz、実シリコン動作確認済）。
- TR-1um（1 µm, 2層メタル, コア 1,840×1,840 µm = 3.39 mm²）に対し、
  既存 STDLIB での素直な合成は **素セル面積 3.80 mm²（NAND2換算 2,085ゲート）**
  → **そのままでは入らない（約2倍オーバー）**。
- 速度は全く問題なし。**面積のみがボトルネック**。
- → `05_cell_circuits.md` の方針（**単相クロック / GIOのみ3ステート /
  レジスタ・スタックはカスタムアレイ / TG系最小セル**）を適用すると
  素セル面積 **3.80 → 1.62 mm²**、配置率60%で 2.70 mm² となり **収まる見通し**。

## 設計方針（確定事項）→ 詳細は `06_design_policy.md`

1. **クロックは単相**（φ1/φ2 の2相は廃止）→ パッドが1本空く
2. **3ステートは GIO（双方向I/Oセル）でのみ使用**。内部バスは MUX 化
   ※ `GIO` は TR-1um / IP62 PDK に存在しない（自作前提）
3. **レジスタファイル(16×4bit) + PC/スタック(4×12bit) = 112bit はスクラッチのカスタムアレイ**

自作が必要なセル: `DLATCH`(8-10T) / `DFF`(16T) / `DFFE`(22T) / `ICG`(12T) /
`RFCELL`(6T SRAM または 12T TLAT) / `GIO`(~16T+大W) / `TIE0`,`TIE1`

## 記憶系の構成 → `07_sram6t_macro.md`

- Scratchpad 16w×4b + スタック 12w×4b（4段×3ニブル）= 28w を
  **1本のマクロ `C4004_SRAM32X4`（32word × 4bit = 128bit）に統合**
- ACC/IR/SP/ステートカウンタ等 **29 bit は FF のまま残す**（単一ポートのため）
- ビットセル **604 µm²/bit 確定**（100.7 µm²/Tr）。アレイ 219.6 × 388 µm
- **センスアンプを設計する**（速度のためではなく BL 振幅低減のため）→ `08_senseamp_refs.md`
- **6T マクロ 0.272 mm² ≒ 12T TLAT マクロ 0.281 mm²** —
  128bit 規模では周辺回路が相殺するため、面積目的なら 6T にする利点は無い

## 主要リンク

- https://en.wikipedia.org/wiki/Intel_4004
- https://en.wikichip.org/wiki/intel/mcs-4/4004
- https://www.4004.com/ / https://4004.com/mcs4-masks-schematics-sim.html
- https://tinytapeout.com/chips/ttsky25a/tt_um_mcs4_cpu
- https://github.com/munetomo-maruyama/MCS4_SYSTEM
- https://opencores.org/projects/mcs-4 / https://github.com/freecores/mcs-4
- https://github.com/OpenSUSI/TR-1um
