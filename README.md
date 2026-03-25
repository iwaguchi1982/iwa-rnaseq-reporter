# iwa-rnaseq-reporter

RNA-Seq 解析結果を **Web アプリ上で確認・整理・比較設計** するためのアプリです。  
`iwa-rnaseq-counter` が作成した結果を読み込み、**サンプル構成・QC・発現量・比較条件** を、Dry 解析に不慣れな方でも段階的に確認できることを重視しています。

---

# 1. このアプリは何をするものか

`iwa-rnaseq-reporter` は、RNA-Seq 解析の**後半工程**を支援するアプリです。

具体的には、`iwa-rnaseq-counter` で作成した解析結果を読み込み、

- サンプル一覧の確認
- QC の確認
- 発現量テーブルの確認
- PCA や相関などの予備解析
- 比較したい群の整理
- DEG 解析に向けた比較設計

を、**Web UI で見ながら進める**ことを目的にしています。

このアプリは、コマンドラインやスクリプト操作に慣れていない利用者でも、  
RNA-Seq 解析結果を「見て」「確認して」「比較の準備をする」ための入口として使えるように設計しています。

---

# 2. 想定ユーザー

このアプリは、特に次のような方を想定しています。

- Wet 実験が主な研究者
- Dry 解析の専門家ではないが、RNA-Seq 結果を確認したい人
- 解析担当者と相談しながら比較条件を詰めたい人
- Web アプリで直感的に結果を確認したい人
- 納品前の内容確認や解析設計の下準備をしたい人

---

# 3. 何ができるか

現時点で主に想定している機能は以下です。

- `iwa-rnaseq-counter` の出力結果の読み込み
- dataset の整合性チェック
- サンプル一覧とメタデータの確認
- QC 結果の確認
- gene / transcript レベルの発現量テーブル確認
- PCA / 相関などの exploratory analysis
- 比較したい群の整理
- DEG 解析に向けた比較設計
- レポートや後続解析に渡すための土台作成

---

# 4. 使い方のイメージ

基本的な流れは次の通りです。

1. `iwa-rnaseq-counter` で作成した結果を用意する  
2. `iwa-rnaseq-reporter` で結果を読み込む  
3. サンプル構成・QC・発現量を確認する  
4. 比較したい群を設定する  
5. DEG 解析やレポート作成につなげる  

このアプリは、いきなり複雑な統計設定を求めるのではなく、  
まずは **結果を安全に読み、見て、比較条件を整理する** ところから使えるようにする方針です。

---

# 5. 入力として想定するもの

通常は、`iwa-rnaseq-counter` が出力した結果一式を入力として使います。

利用者目線では、主に次のどちらかがあれば使い始めやすい想定です。

- `iwa-rnaseq-counter` の出力ディレクトリ
- `dataset_manifest.json` を含む結果フォルダ

必要に応じて、サンプル群の比較に使う `sample_metadata.csv` を参照します。

---

# 6. 出力として得られるもの

現段階では主に、

- 確認しやすい Web UI
- exploratory analysis の結果
- 比較設計情報
- DEG 結果の土台
- レポート生成のための構造化データ

を出力対象として想定しています。

将来的には、

- `ResultSpec`
- `ReportPayloadSpec`
- `ExecutionRunSpec`

を通じて、他アプリや report automation とも接続しやすくしていきます。

---

# 7. まず触ってみる人へ

この README の後半には、Dry / 開発者向けの内部設計説明があります。  
まず利用したいだけの方は、細かい内部仕様を読む必要はありません。

最初に気にすればよいのは次の点です。

- counter の結果を読み込めること
- サンプル一覧と QC を確認できること
- 比較したい群を整理できること
- Web UI で段階的に解析を進められること

---

# 8. 現在の位置づけ

`iwa-rnaseq-reporter` は、`iwa-rnaseq-counter` の次段に位置する  
**RNA-Seq Suite の解析・可視化・比較設計モジュール**です。

役割を一言でいうと、

- `counter` が「結果を作るアプリ」
- `reporter` が「結果を読んで確認し、比較設計へ進めるアプリ」

です。

---

---

# 9. Dry / 開発者向けメモ

ここから下は、Dry 解析担当者・開発者・将来保守者向けの説明です。

---

# 10. v0.2.0 の位置づけ

`v0.2.0` では、`iwa-rnaseq-reporter` を

**Spec-aware RNA-Seq analysis / comparison entrypoint**

として整理することを目標にしています。

この時点で重視しているのは、機能を大量追加することよりも、  
**I/O 契約と比較解決の責務分離を安定化すること**です。

---

# 11. 現在の基本構造

現在の reporter は、大きく次の4段階で動くことを想定しています。

1. **LOAD**  
   `MatrixSpec` と `ComparisonSpec` を読み込み、matrix 実体をロードする

2. **RESOLVE**  
   `sample_metadata.csv` を参照し、comparison criteria を具体的な specimen 群に解決する

3. **EXECUTE**  
   解決済み group 情報をもとに DEG や exploratory analysis を実行する

4. **EMIT**  
   `ResultSpec`, `ReportPayloadSpec`, `ExecutionRunSpec` を出力する

この分離により、

- runner は orchestration
- resolver は比較条件の解決
- analysis engine は統計処理

という責務に分けています。

---

# 12. Spec-aware Pipeline の考え方

`v0.2.0` では、reporter は主に以下を前提にします。

## 入力
- `MatrixSpec`
- `ComparisonSpec`
- `MatrixSpec.metadata.sample_metadata_path` が指す `sample_metadata.csv`

## 出力
- `ResultSpec`
- `ReportPayloadSpec`
- `ExecutionRunSpec`

ポイントは、`ComparisonSpec` が sample ID の固定列挙ではなく、  
**rule-based な comparison 定義**を持つことです。

例:
- `group_labels = case`
- `group_labels = control`

このルールを実際の specimen 群へ解決する役割を、`comparison_resolver.py` が担います。

---

# 13. Comparison 解決の考え方

`ComparisonSpec` は「何を比較したいか」を表し、  
実際にどのサンプルが対象になるかは `sample_metadata.csv` を参照して解決します。

つまり、

- `ComparisonSpec` = 比較ルール
- `sample_metadata.csv` = 比較対象表
- `ResolvedComparisonPlan` = 実行可能な比較計画

という役割分担です。

これにより、`runner.py` や統計処理側に comparison の意味解釈を埋め込まずに済みます。

---

# 14. sample_metadata.csv について

現時点では、最低限次の列を持つ CSV を想定しています。

```csv
specimen_id,subject_id,visit_id,sample_name,group_labels,timepoint_label,batch_label,pairing_id,include_flag,note
```

最小必須として重視しているのは次の列です。

- specimen_id
- subject_id
- group_labels

include_flag は除外制御、
timepoint_label や batch_label は今後の拡張に効きます。

原則として、matrix の列名は specimen_id と対応づけ可能であることを前提にしています。

# 15. dry-run について
v0.2.0 では、開発や配線確認のために dry-run をサポートする方針です。

dry-run では、必要に応じて dummy matrix を使って flow を確認できるようにしています。
本実行では、MatrixSpec.matrix_path が指す実体ファイルを読み込みます。

つまり、

- dry-run = 流れ確認
- 本実行 = 実データ処理

という位置づけです。

# 16. legacy path について

本アプリはもともと、iwa-rnaseq-counter の legacy dataset contract を読む Web アプリとして始まりました。
そのため、現在も一部に legacy path との互換を意識した構造が残っています。

legacy path では、主に次のような成果物を入口にしていました。

dataset_manifest.json
sample_metadata.csv
sample_qc_summary.csv
gene_tpm.csv
gene_numreads.csv
run_summary.json

v0.2.0 では、これを完全に捨てるのではなく、
**Spec-aware path を主経路にしつつ、互換性を段階的に整理する** 方針です。

# 17. 現時点の設計方針

このアプリでは、Oncology を初期主戦場にしつつも、
I/O 契約そのものは disease-agnostic に保つことを重視しています。

そのため、共通 contract の必須項目に次のような領域固有情報は入れません。

- tumor / normal
- stage
- survival endpoint
- RECIST response
- immune hot / cold

必要になった場合は、metadata や将来の overlay / preset で扱う方針です。

# 18. runner / resolver / analysis engine の責務
runner
- spec を読む
- flow を制御する
- 各コンポーネントを接続する
- 最終出力を書く

comparison_resolver
- ComparisonSpec と sample_metadata.csv をもとに群を解決する
- overlap / 不整合 / unsupported criteria を検出する
- ResolvedComparisonPlan を返す

analysis engine
- 解決済み group を入力に統計処理を行う
- comparison rule の意味解釈は持たない

この責務分離は、将来 paired, covariates, sample_selector, timepoint-based analysis を追加する際にも有効です。

# 19. 現在の対応範囲

現時点では、主に次を重視しています。

- comparison resolver の導入
- sample metadata reader / validator
- ResolvedComparisonPlan ベースの解析入口
- ResultSpec, ReportPayloadSpec, ExecutionRunSpec の出力土台
- 最小限のテスト整備

一方で、以下は今後の拡張対象です。

- sample_selector の本実装
- paired design の厳密整合
- covariate 対応の強化
- public comparator との接続
- signature scorer との接続
- report automation との本格統合

# 20. 開発メモ

いまの reporter は、単なる preview app ではなく、
Spec-aware な解析コンポーネントとして再整理中です。

そのため、今後の実装では次を優先します。

- contract を壊さない
- comparison 解決を runner に戻さない
- domain 固有語彙を共通 spec に入れすぎない
- まず RNA-Seq Suite の接続を固める

# 20. 開発メモ

いまの reporter は、単なる preview app ではなく、
Spec-aware な解析コンポーネントとして再整理中です。

そのため、今後の実装では次を優先します。

- contract を壊さない
- comparison 解決を runner に戻さない
- domain 固有語彙を共通 spec に入れすぎない
- まず RNA-Seq Suite の接続を固める

# 21. 関連アプリ
iwa-rnaseq-counter
FASTQ から定量結果を作る producer
iwa-rnaseq-reporter
結果を読み、確認・比較設計・後段解析へつなぐ consumer / analysis entrypoint

将来的には、この2つを中心に RNA-Seq Suite を形成していく想定です。

# 22. 今後

今後は、以下を段階的に進める予定です。

- examples の正式整備
- CONTRACTS.md の共有と安定化
- counter / reporter 間の接続確認
- report export や comparator の拡張
- v0.2.x 系の安定化