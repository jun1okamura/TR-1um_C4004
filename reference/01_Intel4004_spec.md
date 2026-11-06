# Intel 4004 スペック調査

調査日: 2026-09-08 / 対象: TR-1um_C4004 プロジェクト

## 1. チップ諸元（オリジナル 1971年）

| 項目 | 値 |
|---|---|
| 発表 | 1971-11-15（発売価格 $60） |
| プロセス | 10 µm **P-MOS** シリコンゲート（enhancement load） |
| トランジスタ数 | 2,300（諸説 2,250。実チップ抽出値は後述） |
| ダイサイズ | 約 12 mm²（3 mm × 4 mm） |
| パッケージ | **16ピン DIP**（セラミック / プラスチック） |
| 電源 | VDD = −15 V ±5%（VSS基準。+5V/−10V 表記の資料もあり） |
| 消費電力 | 約 1 W |
| クロック | 2相ノンオーバーラップ φ1/φ2、最大 740〜750 kHz |
| 命令サイクル | 10.8 µs（8クロック = 1マシンサイクル） |
| 性能 | 約 92,000 命令/秒 |
| 動作温度 | 0〜70 ℃ |

> 注: 4004.com のリバースエンジニアリング結果では、レイアウト抽出ネットリストは
> **Tr 1,807 / 抵抗 427 / 容量 66**、回路図側は **Tr 1,741 / 抵抗 427**。
> 「2300トランジスタ」は負荷素子や寄生を含めた当時の公称値と考えられる。
> → **CMOS 化する際の実トランジスタ数見積りはこの 1,800 前後を基準にすべき。**

## 2. アーキテクチャ

- データ幅: **4 bit**（BCD指向）
- アドレス幅: 12 bit（4,096 バイトの ROM 空間）
- レジスタ: アキュムレータ 1 本 + **インデックスレジスタ 16 本 × 4 bit**（scratchpad = 64 bit）
- スタック: **3段**（+ PC = 実質 4 × 12 bit = 48 bit のアドレススタック）
- 命令セット: **46命令**（8bit 命令 41、16bit 命令 5）
- RAM: 直接アドレス可能 640 バイト（1,280 × 4bit キャラクタ）
- バス: **4bit 多重化バス 1本**でアドレス／命令／データを時分割転送

## 3. 内部ステート（8ステート/サイクル）

`A1 → A2 → A3 → M1 → M2 → X1 → X2 → X3`

- A1/A2/A3: PC を下位→中位→上位の順に 4bit ずつ ROM へ出力
- M1/M2: 命令を上位/下位 4bit ずつ取り込み
- X1/X2/X3: 実行フェーズ

## 4. ピン配置（16ピン DIP）

| 信号 | 方向 | 本数 |
|---|---|---|
| D0–D3 | 双方向（3ステート） | 4 |
| SYNC | 出力 | 1 |
| CM-ROM | 出力 | 1 |
| CM-RAM0–3 | 出力 | 4 |
| TEST | 入力 | 1 |
| RESET | 入力 | 1 |
| φ1, φ2 | 入力 | 2 |
| VDD, VSS | 電源 | 2 |
| **合計** | | **16** |

→ 信号 14 本 + 電源 2 本。**TR-1um の OSS_FRAME（信号14 + VDD + VSS = 16パッド）と完全に一致する。**

## 5. MCS-4 ファミリ

| 品種 | 機能 |
|---|---|
| 4001 | 256 バイト ROM + 4bit I/O ポート |
| 4002 | 40 バイト（80×4bit）RAM + 4bit 出力ポート |
| 4003 | 10bit シリアル入力／パラレル出力シフトレジスタ |
| 4008/4009/4269/4289 | 標準メモリ接続用インタフェース |

後継: **4040**（1974年、24ピン、命令追加・スタック7段）

## 出典

- [Intel 4004 - Wikipedia](https://en.wikipedia.org/wiki/Intel_4004)
- [4004 - Intel - WikiChip](https://en.wikichip.org/wiki/intel/mcs-4/4004)
- [Intel 4004 — 50th Anniversary Project (4004.com)](https://www.4004.com/)
- [Complete Artwork, Schematics, and Simulator for Intel MCS-4](https://4004.com/mcs4-masks-schematics-sim.html)
- [Intel's revolutionary 54-year-old 4004 chip (Tom's Hardware)](https://www.tomshardware.com/pc-components/cpus/cpu-collector-exposes-microscopic-insides-of-intels-revolutionary-4004-chip-10-000nm-chip-was-the-worlds-first-programmable-microchip-processor)
