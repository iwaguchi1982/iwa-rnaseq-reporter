> **Note**  
> `v0.1.5` is an exploratory reader / validator / analysis-preview release.  
> Statistical DEG testing and report export are not included yet.

`iwa-rnaseq-reporter` は、`iwa-rnaseq-counter` が出力した RNA-Seq 定量結果セットを読み込み、  
**dataset の整合確認・要約表示・QC/metadata preview** を行う Streamlit アプリです。

現時点の `v0.1.0` は、**report 生成本体ではなく、reader / validator / preview UI** を提供する初期リリースです。

---

## 1. 目的

`iwa-rnaseq-counter` の後段として、以下を担います。

- counter 出力 contract を安全に読み込む
- dataset 単位で必須成果物の有無を確認する
- sample metadata / sample QC summary / expression matrix の整合を確認する
- 後段の可視化・解析・レポート生成に渡せる土台を作る

---

## 2. 現在の対応範囲 (`v0.1.3`)

### 対応していること

- `dataset_manifest.json` を入口とした dataset 読込
- run directory / results directory / manifest file の3入力に対応
- required / optional file の存在確認
- `sample_metadata.csv` の読込と正規化
- `sample_qc_summary.csv` の読込と正規化
- `gene_tpm.csv` / `gene_numreads.csv` の読込
- `transcript_tpm.csv` / `transcript_numreads.csv` の optional 読込
- sample ID 整合性チェック
- validation message 表示
- dataset overview 表示
- sample metadata / QC summary preview 表示
- analysis matrix 構築
  - matrix kind 切替
  - `exclude` 反映
  - `log2(x+1)` 切替
  - feature filtering (`min nonzero samples`, `min feature mean`)
- PCA preview
- sample correlation preview
- gene / feature search
- top variable features table
- DEG comparison design scaffold
- DEG preview table scaffold（統計検定なし）

### まだ対応していないこと

- 統計的 DEG 解析本体（p-value / adjusted p-value）
- volcano plot
- DEG heatmap
- GO / pathway enrichment
- PDF / HTML report export
- transcript-level 専用解析UIの本格実装

---

## 3. 対応する入力 contract

本バージョンは、主に **`iwa-rnaseq-counter v0.1.7` の出力 contract** を想定しています。

### 想定入口

以下のいずれかを入力できます。

- run directory  
  例: `run_results/yeast_run_014`
- results directory  
  例: `run_results/yeast_run_014/results`
- manifest file  
  例: `run_results/yeast_run_014/results/dataset_manifest.json`

### 想定ファイル構成

```text
run_results/<run_name>/
├── results/
│   ├── dataset_manifest.json
│   ├── run_summary.json
│   ├── sample_metadata.csv
│   ├── sample_qc_summary.csv
│   ├── gene_tpm.csv
│   ├── gene_numreads.csv
│   ├── transcript_tpm.csv          # optional
│   └── transcript_numreads.csv     # optional
├── sample_sheet.csv                # optional
├── run_config.json                 # optional
└── logs/
    └── run.log                     # optional

## 4. dataset_manifest.json について
v0.1.0 は、現行の legacy manifest 形式を受け付けます。  
例:  
```json
{
  "app_name": "iwa-rnaseq-counter",
  "app_version": "v0.1.7",
  "run_name": "yeast_run_014",
  "analysis_name": "yeast_run_014",
  "input_source": "auto_detect",
  "quantifier": "salmon",
  "quantifier_version": "1.10.1",
  "sample_count_total": 2,
  "sample_count_success": 2,
  "sample_count_failed": 0,
  "sample_ids_all": ["SRR518891", "SRR518892"],
  "sample_ids_success": ["SRR518891", "SRR518892"],
  "sample_ids_failed": [],
  "sample_ids_aggregated": ["SRR518891", "SRR518892"],
  "files": {
    "sample_metadata": "results/sample_metadata.csv",
    "sample_qc_summary": "results/sample_qc_summary.csv",
    "transcript_tpm": "results/transcript_tpm.csv",
    "transcript_numreads": "results/transcript_numreads.csv",
    "gene_tpm": "results/gene_tpm.csv",
    "gene_numreads": "results/gene_numreads.csv",
    "run_summary": "results/run_summary.json",
    "sample_sheet": "sample_sheet.csv",
    "run_config": "run_config.json",
    "run_log": "logs/run.log"
  }
}
```
将来的には schema_name, schema_version, dataset_id, paths を持つ新schemaへの移行を想定していますが、v0.1.0 は legacy 互換ローダーを優先しています。

## 5. バリデーション方針
### fatal

以下は dataset 読込失敗とします。

- dataset_manifest.json を解決できない
- required file が見つからない
- sample_metadata.csv に sample_id がない
- sample_qc_summary.csv に sample_id がない
- gene_tpm.csv / gene_numreads.csv の sample 列が一致しない
- gene matrix に sample 列が存在しない

### warning
以下は読込継続可能とし、UI に表示します。

- transcript matrix が存在しない
- metadata にだけ存在する sample がある
- QC summary にだけ存在する sample がある
- sample_ids_aggregated と matrix sample がずれる
- failed sample が matrix に含まれる

## 6. 画面構成 (`v0.1.3`)

- Input
- Load Status
- Dataset Overview
- Sample ID Summary
- Validation Messages
- Sample Metadata
- Sample QC Summary
- Analysis Setup
- PCA Preview
- Sample Correlation
- Gene Search
- Top Variable Features
- DEG Comparison Design
- DEG Preview Table

## 7. 動作環境
- Python 3.12 系を推奨
- Streamlit
- pandas
- pytest

## 8. セットアップ例
pixi を使う場合
```
pixi install
pixi run streamlit run iwa_rnaseq_reporter.py
```
仮想環境 + pip の場合
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run iwa_rnaseq_reporter.py
```
## 9. テスト
```
pytest -q
```

## 10. 使い方
1. アプリを起動する
1. Dataset or Manifest Path に以下のいずれかを入力する
  - run directory
  - results directory
  - dataset_manifest.json
1. Load Dataset を押す
1. Load Status で file 解決状態を確認する
1. Dataset Overview で sample 数・feature 数を確認する
1. Validation Messages で fatal / warning / info を確認する
1. Sample Metadata / Sample QC Summary を確認する

## 11. 現時点での位置づけ
`iwa-rnaseq-reporter v0.1.3` は、
**iwa-rnaseq-counterの出力を読み込み、exploratory analysis と comparison design まで行える初期 reporter** です。

この段階で利用できるもの:

- contract reader
- dataset validator
- preview UI
- exploratory analysis (PCA / sample correlation)
- gene / feature search
- DEG comparison design scaffold
- DEG preview table scaffold

この段階でまだ未対応のもの:

- 統計的 DEG 解析本体
- 多重検定補正付き結果表
- volcano / enrichment / report export

## 12. 今後の予定

今後の候補機能:
- PCA
- sample correlation heatmap
- DEG table
- volcano plot
- top DEG heatmap
- gene search
- enrichment analysis
- PDF / HTML report export

## 13. 開発ノート
### DEG Comparison / Preview について
`DEG Comparison Design` と `DEG Preview Table` は、現在は **comparison scaffold / preview** 機能です。

- comparison-ready な metadata 列（例: `group`, `condition`）が存在する場合に比較設計を行えます
- 現在の analysis matrix 設定をもとに comparison-ready matrix を構築します
- `DEG Preview Table` は統計検定を含まず、主に以下を表示します
  - グループ平均
  - log2倍率変化（preview）
  - 非ゼロカウント

比較に使える metadata 列が存在しない場合、DEG preview は実行されません。

### DEG Preview Table
DEGプレビューテーブルは、選択したグループA/グループBの比較を探索的に表示します。

現在のプレビュー列は以下のとおりです。
- `mean_group_a`
- `mean_group_b`
- `log2_fc`
- `abs_log2_fc`
- `direction`
- `rank`
- `nonzero_group_a`
- `nonzero_group_b`

このテーブルは、完全な統計的DEG結果テーブルではなく、比較のための枠組みとして設計されています。
現段階では、正式な統計検定を実施する前に、ユーザーが大きな発現差を迅速に確認するのに利用してください。
> `direction`は、`log2_fc`の符号に基づいて、ある特徴量がグループAとグループBのどちらで高いかを示します。
> `rank`は`abs_log2_fc`の降順に基づいて割り当てられるため、ランクの高い行ほどプレビューレベルでの発現量の差が大きいことを示します。

### Comparison Design Consistency
DEG比較設定は、現在の解析サンプルセットと解析マトリックスに基づいて解決されます。
つまり、DEGプレビュー入力が組み立てられる前に、以下の設定が反映されます。
- 選択された行列の種類
- オプションの log2(x+1) 変換
- 除外ベースのサンプルフィルタリング
- 特徴フィルタリングの閾値

結果として、比較サンプルテーブル、DEG入力マトリックス、およびDEGプレビュー出力は、構造上常に整合した状態に保ちます。
> 比較候補列は、グループベースの比較において意味のあるメタデータフィールドを優先するようにフィルタリングされます。 
> すべて一意の識別子のように振る舞う列は、候補選択から除外されます。

### Current Scope of DEG Preview
現在のDEGプレビュー版では、統計的検定は**まだ**実行できません。
今後のバージョンでは、以下の機能が予定されています。
- p値
- 調整済みp値
- 統計的DEG検定
- volcano plots
- DEG heatmaps
- エンリッチメント解析


### Analysis Setup について
`Analysis Setup` では、後続の PCA / sample correlation / gene search / variable feature ranking / DEG preview に共通で使う analysis matrix を定義します。

主な設定項目:
- matrix kind
  - `gene_tpm`
  - `gene_numreads`
  - `transcript_tpm` (available if present)
  - `transcript_numreads` (available if present)
- `Apply log2(x+1)`
- `Respect exclude column`
- `Min nonzero samples per feature`
- `Min feature mean`

PCA や correlation は、この current analysis matrix を前提に計算されます

### PCA Preview / Sample Correlation について
- `PCA Preview` は exploratory purpose の可視化です
- sample 数が少ない場合、解釈には注意が必要です
- `Sample Correlation` は current analysis matrix に基づく sample-to-sample correlation を表示します 

### その他
- iwa-rnaseq-counter の成果物 contract を前提に実装
- legacy manifest 互換を優先
- UI より先に loader / validator / normalizer / tests を固める方針

## License
This repository is distributed under the **Iwa Collections Non-Resale License 1.0**.
Commercial resale of the software itself, or paid redistribution of derivative versions where the software is the primary value, is prohibited.
本リポジトリは **Iwa Collections Non-Resale License 1.0** で公開しています。  
ソフトウェア自体の有償販売、および本ソフトウェアが主たる価値となる派生物の有償再配布は禁止です。