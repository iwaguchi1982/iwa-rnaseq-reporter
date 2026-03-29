# Developer_README

## この文書の目的

この文書は `iwa-rnaseq-reporter` の開発者向け内部整理である。対象は、現状の状態、基準、契約、データフロー、および表示契約を崩さないための判断基準の共有にある。利用者向けの説明は `README` に置き、この文書では annotation 契約、表示契約、counter から受け取る成果物の前提を扱う。

## このアプリの責務

`iwa-rnaseq-reporter` の責務は、counter などが出力した matrix / metadata / annotation を読み、比較条件を整理し、差次的発現結果や可視化を利用者に分かりやすく提示することにある。

このアプリは次を担当する。

- matrix と sample metadata を読む
- comparison 条件を解決する
- DEG を計算し、比較結果を整形する
- gene symbol と feature_id を安定して扱う
- 表、検索、プロットで一貫したラベルを使う
- 後続の enrichment や可視化拡張へつながる結果契約を維持する

このアプリは quant 実行の責務を持たない。FASTQ 処理、backend job 管理、run artifact の生成は counter 側の責務である。

## 現状の状態

現状では、annotation を optional input として読み、annotation があれば `gene_symbol` を使い、無ければ `feature_id` へ fallback する方向が入っている。`display_label` を UI 用最終ラベルとして扱う土台があり、DEG table、Volcano、Top genes、gene search などへ適用が進んでいる。

v0.5 系の主題は、これを「よさそうな実装」ではなく「固定した表示契約」にすることにある。

## 入力契約

### 必須入力

reporter が最低限読むべきものは次である。

- matrix
- sample metadata
- comparison 条件

### optional 入力

annotation は optional である。`feature_annotation.tsv` があれば使い、無ければ `feature_id` fallback で動作する。

### annotation 契約

`feature_annotation.tsv` は reporter 表示用 annotation 契約である。最低限、次の列を持つ。

- `feature_id`
- `gene_symbol`

`feature_id` は真キーであり、annotation merge の join key でもある。`gene_symbol` は表示候補であり、識別キーではない。

`feature_id` 列が無い annotation は無効扱いにする。`gene_symbol` 列が無い、または値が空のときは warning を許容し、`feature_id` fallback とする。

## 表示契約

### 真キー

真キーは常に `feature_id` である。これは内部結合、比較結果追跡、export の参照キーとして維持する。

### `gene_symbol`

`gene_symbol` は annotation 由来の表示候補である。存在しても識別キーには使わない。重複や欠損を許容する。

### `display_label`

`display_label` は UI 用最終ラベルである。生成規則は固定する。

- `gene_symbol` が存在し空でない場合は `display_label = gene_symbol`
- それ以外は `display_label = feature_id`

下流の表示関数で独自に fallback を散らさず、上流で `display_label` を作り、主要表示面はそれを読む構造へ寄せる。

## display_label の適用確認済み表示面

v0.5.0 時点では、`display_label` を reporter における UI 用最終ラベルとして扱う。`feature_id` は真キー、`gene_symbol` は表示候補であり、`display_label` は `gene_symbol` 優先、無ければ `feature_id` fallback で決定する。適用確認済みの主要表示面は、DEG table、Volcano plot の annotation text、Volcano plot の hover、Top Up / Top Down genes、gene search 結果表示である。export では `display_label` のみを残すのではなく、`feature_id` と `gene_symbol` の両方を保持する。

## データフロー

### loader での処理

1. matrix と sample metadata を読む
2. annotation を探索する
3. annotation があれば `feature_id` で merge する
4. `gene_symbol` を保持する
5. `display_label` を作る
6. comparison を解決する
7. DEG と可視化用表を作る

### annotation 探索

reporter は annotation を複数の入口から探してよいが、優先順位は実装上で固定する。manifest / spec に annotation path があればまずそれを使い、無ければ標準配置を探し、それも無ければ annotation 無しとして fallback する。

### counter から受け取る前提

counter 側が annotation を生成できた場合、標準配置は `results/feature_annotation.tsv` である。`feature_annotation_path` はこの annotation 契約ファイルへの参照であり、`tx2gene` の代用品ではない。

## 実装上の基準

### 保つべきこと

- feature_id を真キーとして維持する
- gene_symbol を識別キーにしない
- display_label を UI 表示の共通入口にする
- annotation が無い場合でも reporter 自体は成立させる
- export に feature_id / gene_symbol の両方を残す

### 避けるべきこと

- 表示関数ごとに独自 fallback を増やすこと
- `gene_symbol` を一意キーとして扱うこと
- annotation が無いだけで表示を落とすこと
- counter の backend 固有事情を reporter 側へ持ち込むこと

## 表示面ごとの運用ルール

### DEG table

主表示ラベルは `display_label` を使う。追跡のため `feature_id` と `gene_symbol` を保持する。

### Volcano plot

annotation text と hover は `display_label` 契約に従う。過密時の省略は許容するが、適用ルール自体を変えない。

### Top Up / Top Down

主要 gene 表示は `display_label` を使う。比較結果追跡のため内部では `feature_id` を保持する。

### gene search

検索結果一覧の表示ラベルは `display_label` を使う。hit の識別は `feature_id` に基づいて行う。

### export

display_label は補助列として扱ってよいが、`feature_id` と `gene_symbol` を必ず残す。

## 変更時の確認項目

- annotation がある場合に `gene_symbol` が使われるか
- annotation が無い場合に `feature_id` fallback で壊れないか
- DEG table、Volcano、Top genes、gene search で表示契約が揃っているか
- export に `feature_id` / `gene_symbol` が残っているか
- counter から受け取る annotation 契約と README / 実装がずれていないか

## project_root 配下の必要ディレクトリと主要ファイル

以下は、開発時に意味を理解しておくべき最小構成である。

### `project_root/app.py`

Streamlit の GUI 入口である。利用者向けの比較設定、可視化、検索、結果表示を束ねる。

### `project_root/cli.py`

CLI 入口である。GUI 非依存の実行導線を持つ。

### `project_root/src/iwa_rnaseq_reporter/models/`

内部契約モデル群を置く。`matrix.py`、`comparison.py`、`result.py`、`report_payload.py` などが reporter の中心となる。

### `project_root/src/iwa_rnaseq_reporter/io/`

Spec / payload / metadata の入出力を置く。counter 側成果物との handoff 境界でもある。

### `project_root/src/iwa_rnaseq_reporter/pipeline/`

比較解決や runner を置く。アプリ全体の処理フローをまとめる層である。

### `project_root/src/iwa_rnaseq_reporter/legacy/`

現行 reporter の主要処理が集まる。`loader.py`、`analysis.py`、`gene_search.py`、`deg_stats.py`、`pca_utils.py`、`correlation_utils.py` などがある。現時点ではここが実働の中心であり、display_label 契約や fallback の確認対象でもある。

### `project_root/README.md`

利用者向け README である。比較の流れ、入力、結果の見方を説明する場であり、内部契約の細部はここに出しすぎない。

### `project_root/Developer_README.md`

この文書である。annotation 契約、display_label 契約、counter から受け取る前提、主要表示面の基準を整理する。
