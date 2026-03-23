# iwa-rnaseq-reporter v0.1.0

初回公開版です。

## 概要

`iwa-rnaseq-reporter v0.1.0` は、`iwa-rnaseq-counter` の出力 dataset を読み込み、  
dataset 単位の整合確認と preview を行うための最初のリリースです。

本バージョンは、**report 自動生成本体ではなく、reader / validator / preview UI** に焦点を当てています。

---

## Added

- `dataset_manifest.json` を入口とした dataset loader
- run directory / results directory / manifest file の自動解決
- required / optional files の存在確認
- `sample_metadata.csv` 読込
- `sample_qc_summary.csv` 読込
- `gene_tpm.csv` / `gene_numreads.csv` 読込
- `transcript_tpm.csv` / `transcript_numreads.csv` の optional 読込
- sample ID consistency validation
- validation messages 表示
- Load Status UI
- Dataset Overview UI
- Sample Metadata preview
- Sample QC Summary preview
- pytest ベースの loader / validator / manifest / normalizer テスト基盤

---

## Supported contract

主に `iwa-rnaseq-counter v0.1.7` の出力 contract を想定しています。

---

## Known limitations

- PCA 未実装
- correlation 未実装
- DEG 未実装
- enrichment 未実装
- PDF / HTML export 未実装
- transcript-level 専用可視化は未実装
- QC 指標の高度な解釈は今後の課題

---

## Positioning

このバージョンは、`iwa-rnaseq-reporter` を

- contract reader
- dataset validator
- preview UI

として成立させるための初期マイルストーンです。