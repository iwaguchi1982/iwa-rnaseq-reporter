# iwa-rnaseq-reporter
> **Note**
> v0.1.0 is an initial reader / validator / preview release.
> Downstream analytics and report generation are not included yet.

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

## 2. 現在の対応範囲 (`v0.1.0`)

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

### まだ対応していないこと

- PCA
- sample correlation
- DEG 解析
- volcano plot
- heatmap
- GO / pathway enrichment
- PDF / HTML report export
- gene search / transcript search の本格UI

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

## 6. 画面構成 (v0.1.0)
- Input
- Load Status
- Dataset Overview
- Sample ID Summary
- Validation Messages
- Sample Metadata
- Sample QC Summary

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
iwa-rnaseq-reporter v0.1.0 は、
counter 出力を読むための最初の入口アプリです。

この段階では、解析結果の高度な可視化や納品レポート生成ではなく、
- contract reader
- dataset validator
- preview UI
として安定させることを優先しています。

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

## 13. 開発メモ
- iwa-rnaseq-counter の成果物 contract を前提に実装
- legacy manifest 互換を優先
- UI より先に loader / validator / normalizer / tests を固める方針

## License

This repository is distributed under the **Iwa Collections Non-Resale License 1.0**.
Commercial resale of the software itself, or paid redistribution of derivative versions where the software is the primary value, is prohibited.
本リポジトリは **Iwa Collections Non-Resale License 1.0** で公開しています。  
ソフトウェア自体の有償販売、および本ソフトウェアが主たる価値となる派生物の有償再配布は禁止です。