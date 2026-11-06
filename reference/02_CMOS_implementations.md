# 4004 の CMOS / HDL 実装事例

## A. Tiny Tapeout「39 MCS-4 4004 CPU」— 最重要参考例 ★

| 項目 | 内容 |
|---|---|
| 設計者 | 丸山 宗智 (Munetomo Maruyama) |
| プロセス | **SkyWater SKY130（130 nm CMOS）**, shuttle `ttsky25a` |
| 記述 | Verilog HDL（4004 CPU コアをフルスクラッチで論理設計） |
| 実装規模 | Tiny Tapeout **1タイル ≒ 2,000ゲート / I/O 24本** に収容 |
| 動作周波数 | **750 kHz**（オリジナル準拠） |
| フロー | **LibreLane**（OpenLane系）で GDSII 生成 |
| 検証 | Busicom 141-PF 電卓プログラムを無改造で実行、実シリコン動作確認済 |
| 実績 | Machin の公式で円周率 500 桁を 750 kHz で約17分で計算 |
| ドキュメント | 100ページ超の Technical Reference Manual (`doc/MCS4_System_TRM.pdf`) |
| ライセンス | CC BY-NC-SA 2.5（141-PF ファームウェア由来） |

**示唆**: CMOS スタンダードセルで 4004 コアは **約2,000ゲート規模**。
16ピン DIP の I/O 本数が TT の 24 I/O にちょうど収まった、という点も本プロジェクトと同じ構図。

- https://tinytapeout.com/chips/ttsky25a/tt_um_mcs4_cpu
- https://github.com/munetomo-maruyama/MCS4_SYSTEM
- https://github.com/munetomo-maruyama/AdventCalendar2025/blob/main/4004.md

## B. OpenCores / freecores "mcs-4"

- 作者: Reece Pollack (2012)、ライセンス CC BY-NC-SA
- Verilog RTL で 4004 + 4001/4002/4003 を実装
- モジュール構成: `i4004.v` / `alu.v` / `scratchpad.v` / `instruction_pointer.v` /
  `instruction_decode.v` / `timing_io.v` / `counter.v`（計 約1,350行）
- 本プロジェクトで Yosys 合成し規模見積りに使用（→ `04_area_estimation.md`）
- https://opencores.org/projects/mcs-4 / https://github.com/freecores/mcs-4

## C. 4004.com（50周年プロジェクト / Lajos Kintli）

- 4001/4002/4003/4004 の **マスクアートワーク・回路図・シミュレータ** を CC BY-NC-SA 3.0 で公開
- 顕微鏡写真からレイアウトを抽出しマスクと突合。
  抽出ネットリスト: Tr 1,807 / R 427 / C 66（回路図側 Tr 1,741 / R 427）
- **オリジナル P-MOS のトランジスタ単位トポロジをそのまま CMOS に写すフルカスタム路線の一次資料**
- https://4004.com/mcs4-masks-schematics-sim.html

## D. その他

- **Retroshield 4004 / 8 Bit Force** — 実 4004 を Arduino で駆動するハーネス（バス検証に有用）
  https://www.8bitforce.com/projects/4004/
- **Jeremy King** — 4004 の再現とパイプライン版の試作
  https://www.hackster.io/news/jeremy-king-sets-his-sights-on-recreating-intel-s-venerable-4004-cpu-and-a-new-pipelined-version-bc1627bcbc02
- **Zama** — 準同型暗号 FPGA 上の 4004 実装（アーキ資料として）
  https://www.zama.org/post/homomorphic-fpga-implementation-of-the-intel-4004-part-1
- **Retro Computing Forum** — 「4004 を Tiny Tapeout で」議論スレッド
  https://retrocomputingforum.com/t/the-4004-in-transistors-and-perhaps-as-a-tiny-tapeout/4762
- **uvicrec** — 4004 のリバースエンジニアリング解説
  http://uvicrec.blogspot.com/2011/09/understanding-intel-4004.html
