# センスアンプ — 1 µm 世代の文献集と TR-1um 向け設計指針

作成: 2026-09-20 / 前提: ビットセル **604 µm²/bit 確定**、BL 負荷 16 cell、5 V、M1/M2 2層

---

## 0. 結論: どれを描くか

**DEC の US4910713A「High input impedance, strobed CMOS differential sense amplifier」
（1988 出願 / 1990 登録）が TR-1um にそのまま移植できる最有力。**

理由:

- **5 V・1 µm 世代のために設計された回路そのもの**（DEC の VAX 用キャッシュ SRAM 由来）
- 入力が MOS ゲートだけ = **高入力インピーダンス**。BL に容量以外の負荷をかけない
  → プリチャージ設計とリードディスターブの検討が SA と分離できる
- **ストローブ 1 本**でセンスとプリチャージを兼ねる → 単相 CLK 方針（`06_design_policy.md`）と合う
- 出力がフルレールまで開く → 後段に追加のレベル復元が要らない
- ラッチ後は **DC 電流ゼロ**
- **特許なので回路図が全部無料で読める**（期限切れ・パブリックドメイン）

対抗は US4843264A（VISIC/AT&T, 1987/1989）の 7 トランジスタ型
「差動対 + 足の引き下げ Tr + 4T ラッチ」。**50–100 mV を 2 ns 以下でラッチ**と明記されており、
必要な BL 振幅の目安が数字で書いてある。まずこの 2 件を読むのが早い。

> なお C4004 の動作は 750 kHz、1 ステート 1.33 µs。**速度のためにセンスアンプは要らない**
> （`07_sram6t_macro.md` §0）。それでも作るなら目的は
> ①BL 振幅を落として消費電力とリードディスターブを減らす
> ②TR-1um で SRAM 一式を成立させる経験を得る ——
> のどちらか。**設計目標をどちらに置くかで最適なトポロジが変わる**ので先に決めること。

---

## 1. 特許 — 1 µm 世代・無料・全回路図つき ★実務的に最有用

学術論文は有料が多いが、**同世代の特許は Google Patents で全文・全図が無料**。
回路図とトランジスタレベルの動作説明が載っているので、実際に描くならこちらが速い。

| 番号 | 表題 | 出願/登録 | 出願人 | 内容 |
|---|---|---|---|---|
| **US4910713A** | High input impedance, strobed CMOS differential sense amplifier | 1988 / 1990 | Digital Equipment | **本命。** たすき掛け対 ×2 + ストローブ 3 Tr。単一ストローブでセンス＋出力プリチャージ。フルレール出力、低消費 |
| **US4843264A** | Dynamic sense amplifier for CMOS static RAM | 1987 / 1989 | VISIC → AT&T | 7 Tr（センス対 2 + 引下げ 1 + 4T ラッチ）。**50–100 mV を 2 ns でラッチ**、ラッチ後 DC 電流ゼロ。64k SRAM で実証 |
| **US5289415A** | Sense amplifier and latching circuit for an SRAM | 1994 | | SA と出力ラッチの繋ぎ方。`07` §6 の「リード結果を外でラッチ」に対応 |
| **US5193076A** | Control of sense amplifier latch timing | 1993 | | **ストローブ `SE` のタイミング生成**。自己タイミング／レプリカの考え方 |
| **US5247479A** | Current sensing amplifier for SRAM | 1993 | | 電流モード。BL 振幅を落としたい場合 |
| **EP0303815B1** | Sense amplifier for a CMOS static memory | 1993 | | 欧州側の同世代実装 |
| **US4247791A** | CMOS memory sense amplifier | 1981 | | 最初期。原理の理解用 |
| **JP2527050B2** | 半導体記憶装置のセンスアンプ回路 | | | 日本語で読める同世代実装 |

いずれも **権利は失効済み**。回路を参考にするのに制約はない。

- https://patents.google.com/patent/US4910713A/en
- https://patents.google.com/patent/US4843264A/en
- https://patents.google.com/patent/US5289415
- https://patents.google.com/patent/US5193076
- https://patents.google.com/patent/US5247479A/en
- https://data.epo.org/gpi/EP0303815B1
- https://patents.google.com/patent/US4247791
- https://patents.google.com/patent/JP2527050B2/en

---

## 2. 基礎論文（JSSC / IEICE、1987–1993）

| 文献 | なぜ要るか |
|---|---|
| **E. Seevinck, F. J. List, J. Lohstroh, "Static-Noise Margin Analysis of MOS SRAM Cells," IEEE JSSC, vol. SC-22, no. 5, pp. 748–754, Oct. 1987.** DOI: 10.1109/JSSC.1987.1052809 | **SNM の定義そのもの。** `07` §10.1 の保持/リード SNM 検証はこの論文の手順で測る。バタフライ曲線の最大内接正方形という基準の出典 |
| **J. Lohstroh, E. Seevinck, J. de Groot, "Worst-Case Static Noise Margin Criteria for Logic Circuits and Their Mathematical Equivalence," IEEE JSSC, vol. SC-18, no. 6, pp. 803–807, Dec. 1983.** | 上の数学的裏付け |
| **E. Seevinck, R. F. Wassenaar, H. C. J. Wallinga, "Current-Mode Techniques for High-Speed VLSI Circuits with Application to Current Sense Amplifier for CMOS SRAM's," IEEE JSSC, vol. 26, no. 4, pp. 525–536, Apr. 1991.** IEEE Xplore doc 75050 | **電流モードセンスの原典。** BL を低インピーダンスでクランプして電流で読む。BL 振幅を極小にしたい場合の理論 |
| **T. Blalock, R. C. Jaeger, "A High-Speed Clamped Bit-Line Current-Mode Sense Amplifier," IEEE JSSC, vol. 26, no. 4, pp. 542–548, Apr. 1991.** | 上と同号。クランプ型の実装側 |
| **"A 6-ns 1-Mb CMOS SRAM with Latched Sense Amplifier," IEEE JSSC / IEICE Trans. Electron. E76-C(5), p. 818, 1993.** IEEE Xplore doc 210031 | **1 Mb 級の実チップでのラッチ型 SA。** この世代の SRAM がどう作られていたかの実例 |
| **B. Wicht, T. Nirschl, D. Schmitt-Landsiedel, "Yield and Speed Optimization of a Latch-Type Voltage Sense Amplifier," IEEE JSSC, vol. 39, no. 7, pp. 1148–1158, Jul. 2004.** | 世代は新しいが、**ラッチ型 SA のオフセットと歩留りの設計式**が最も整理されている。§4 の見積りはこの枠組み |

リンク:
- https://www.semanticscholar.org/paper/Static-noise-margin-analysis-of-MOS-SRAM-cells-Seevinck-List/f87a34b08ccf8587b4f314d3363d4218e9e76b3b
- https://ui.adsabs.harvard.edu/abs/1987IJSSC..22..748S/abstract
- https://ieeexplore.ieee.org/document/75050/
- https://ieeexplore.ieee.org/document/210031/
- https://globals.ieice.org/en_transactions/electronics/10.1587/e76-c_5_818/_p

---

## 3. 書籍

| 書籍 | 位置づけ |
|---|---|
| **T. P. Haraszti, "CMOS Memory Circuits," Kluwer/Springer, 2000/2002.** ISBN 978-0-7923-7950-8 | **これ 1 冊で足りる。** 第 3 章「Sense Amplifiers」が **pp. 163–275 の 113 ページ**。DC/AC/過渡解析、設計手順、電流センスまで体系的。DOI: 10.1007/0-306-47035-7_3 |
| **K. Itoh, "VLSI Memory Chip Design," Springer Series in Advanced Microelectronics 5, 2001.** ISBN 978-3-540-67820-5 | 日立の伊藤清男。**センスとビット線設計の物理的な考え方**。DRAM 寄りだが原理は共通 |
| **B. Prince, "Semiconductor Memories: A Handbook of Design, Manufacture and Application," 2nd ed., Wiley, 1991.** | **まさに 1 µm 世代に書かれたハンドブック。** 当時の実装が素直に載っている |
| **N. Weste, K. Eshraghian, "Principles of CMOS VLSI Design," 2nd ed., Addison-Wesley, 1993.** | 同世代の標準教科書。メモリ章にセンスアンプの基本 |
| **L. Glasser, D. Dobberpuhl, "The Design and Analysis of VLSI Circuits," Addison-Wesley, 1985.** | DEC の設計者による。US4910713A の背景理解に |

---

## 4. トポロジ比較（1 µm 世代で実際に使われた 4 系統）

| | 構成 | Tr | BL 必要振幅 | DC 電流 | TR-1um 適性 |
|---|---|---:|---|---|---|
| **(a) 電圧ラッチ型**（たすき掛け + ストローブ） | US4910713A / US4843264A | 7–10 | 50–150 mV | ラッチ後 0 | **◎ 本命**。小さい、速い、低消費。オフセットが唯一の課題 |
| (b) 電流ミラー型差動アンプ | PMOS ミラー負荷 + NMOS 差動対 + 足 | 5 | 100–200 mV | **常時流れる** | ○ 設計が易しく安定。ただし静的電流。段間バッファとして 1 段目に置く構成が 1 µm 世代の定番 |
| (c) 2 段構成（(b) → (a)） | 電流ミラー + ラッチ | 12–15 | 50 mV | 1 段目のみ | ○ 最も確実。面積は倍 |
| (d) 電流モード / クランプ BL | Seevinck 1991 / Blalock 1991 | 8–12 | **BL 振幅ほぼ 0**（電流で読む） | 常時 | △ BL が長い大容量向け。16 cell では利点が出ない |

**16 cell / BL・5 V・750 kHz という条件では (a) 一択。**
(d) は BL の RC が支配的な大規模アレイのための技術で、今回の規模では複雑さに見合わない。
不安なら (c) にして 1 段目を静的な電流ミラーにする（消費電力は無視できる規模）。

---

## 5. TR-1um 固有の設計制約と目標値

### 5.1 オフセットだけが本当の課題

速度に 1000 倍の余裕がある以上、**SA の性能を決めるのは入力対のミスマッチ**。
`AVT ≈ 20 mV·µm`（tox = 19.5 nm からの概算）として:

| 入力対 W / L | WL | σVT | 対の σΔVT | 3σ | ×1.5（β・負荷ミスマッチ込み） |
|---|---:|---:|---:|---:|---:|
| 10.2 / 1.0 | 10.2 µm² | 6.3 mV | 8.9 mV | 26.6 mV | **39.9 mV** |
| 10.2 / 2.0 | 20.4 µm² | 4.4 mV | 6.3 mV | 18.8 mV | 28.2 mV |
| **20.4 / 2.0** | 40.8 µm² | 3.1 mV | 4.4 mV | 13.3 mV | **19.9 mV** |
| 20.4 / 4.0 | 81.6 µm² | 2.2 mV | 3.1 mV | 9.4 mV | 14.1 mV |

**SA は 4 個しか要らない**（2:1 カラム MUX で 4 bit 出力）ので、
**入力対を大きく取るコストはほぼ無い。W=20.4 / L=2.0 を推奨**（オフセット ~20 mV）。
`AVT` は実測値ではないので、**SPICE のモンテカルロではなく
`vthMN`/`vthMP` を意図的にずらした決定論的な振り方**で確認する
（PDK に統計モデルが無いため。`07` §10.1 と同じ手）。

### 5.2 設計目標

| 項目 | 目標 | 根拠 |
|---|---|---|
| BL 差動振幅（ストローブ時点） | **≥ 200 mV** | オフセット 20 mV に対し 10 倍 |
| センス時間 | < 100 ns | 1 ステート 1.33 µs に対し余裕 |
| プリチャージレベル | VDD（5 V）または VDD−Vth | 高入力インピーダンス型なら VDD でよい |
| ストローブ `SE` 生成 | `WL` 立上りから `DEL2`（~8.8 ns）× 数段 | US5193076A の考え方。レプリカ列は不要 |
| ラッチ後 DC 電流 | 0 | (a) 型を選ぶ理由 |

### 5.3 レイアウト上の制約

- **SA は 2 カラム（2 × 27.45 = 54.9 µm）ピッチに収める**。
  入力対を大きくすると横に入らないので、**縦に伸ばす**（アレイ下の周辺帯を高く取る）。
- M1/M2 しかないので、SA の差動配線は **アレイ直下で M1 縦のまま受ける**。
  BL を横に引き回すと対称性が崩れてオフセットが増える。
- **入力対はコモンセントロイド配置**（2×2 の交差配置）にする。
  1 µm でも配置起因のミスマッチは効く。

---

## 6. 面積への影響（`07_sram6t_macro.md` §9 の更新）

セル 604 µm²/bit（幅 27.45 × 高さ 22 µm と仮定）で:

| | |
|---|---:|
| アレイ 128 bit（16行 × 8列 + タップ行3本） | **0.085 mm²**（219.6 × 388 µm） |
| 周辺（SA ×4 = 24,000 µm² を含む） | 0.162 mm² |
| 配線 +10% | 0.025 mm² |
| **マクロ計** | **0.272 mm²**（外形 ≒ 450 × 588 µm） |

センスアンプを入れてもマクロ面積はほぼ変わらない
（リード受けインバータ 17,328 µm² が SA 24,000 µm² に置き換わるだけ）。

---

## 7. 次の一手

1. **目的を決める**（§0 の ①低消費・低ディスターブ / ②経験）。①なら BL 振幅を
   どこまで落とすかが設計仕様になる。
2. **US4910713A と US4843264A の図を読む**（無料・即読める）。
3. その回路を TR-1um の W/L に置き換えて ngspice で
   **オフセット掃引**（`vthMN` を片側だけ ±10/20/30 mV ずらして誤判定する点を探す）。
4. BL 差動が 200 mV に達する時刻を、16 cell 負荷の実アレイ抽出で確認。
5. `scripts/char/` に SA 用のデッキを足して、`SE` タイミングのマージンを表にする。

## 入手について

学術論文は IEEE Xplore が有料。**特許（§1）と書籍（§3）で実務は足りる。**
Seevinck 1987（SNM）は Semantic Scholar / ADS 経由で本文が見つかることが多い。
IEICE の同世代論文は `globals.ieice.org` にあるが、記事ページの URL が変わっているので
IEEE Xplore 側（doc 210031）から辿るのが確実。
