# v0.5.0 issue

## この repo での目的

`iwa-rnaseq-reporter` 側では、v0.5.0 において annotation と DEG 表示契約を固定する。  
今回の主題は、report の見た目だけをいじることではなく、`feature_id` を真キーにしたうえで `gene_symbol` を表示優先に使う契約を安定化し、Volcano / Top genes / table の表示整合を取ることにある。

## スコープ

### 1. `feature_annotation.tsv` 読み込み正式化
- `feature_annotation.tsv` を optional input として扱う
- join key は `feature_id`
- annotation があれば `gene_symbol` を使う
- annotation が無ければ `feature_id` fallback
- `feature_id` 列が不足している場合の挙動を整理する

最小契約列
- `feature_id`
- `gene_symbol`

### 2. `display_label` 安定化
内部的に少なくとも以下の列を安定して持つ。

- `feature_id`
- `gene_symbol`
- `display_label`

表示ルール
- `display_label = gene_symbol` を優先
- gene symbol が無ければ `display_label = feature_id`

### 3. DEG 表示契約の統一
以下で同じ表示契約を使う。

- Volcano
- Top Up / Top Down genes
- DEG table
- gene search 系表示

表示方針
- ラベル表示は `gene_symbol` 優先
- fallback は `feature_id`
- 詳細表示や export では両方残す

### 4. human / yeast の確認
- human でラベル混雑時に大崩れしないか
- yeast で symbol が無いケースでも壊れないか
- duplicate symbol / missing symbol を最低限確認する

## タスクリスト

- `feature_annotation.tsv` の読込経路を整理する
- dataset layer に annotation を正式に組み込む
- `display_label` 生成ロジックを共通化する
- Volcano / Top genes / table の表示ルールを揃える
- human データでラベル密度を確認する
- yeast / human で fallback 動作を確認する
- export 列に `feature_id` / `gene_symbol` が残ることを確認する

## 確認ポイント

- annotation がある場合に `gene_symbol` を使えているか
- annotation が無い場合に `feature_id` fallback で動くか
- Volcano と table と Top genes で同じ gene を追えるか
- human でラベルが過密でも最低限読めるか
- symbol 欠損時に UI が壊れないか

## 完了条件

- annotation あり / なし両方で reporter が安定動作する
- `feature_id` / `gene_symbol` / `display_label` の役割が固定されている
- Volcano / Top genes / table の表示契約が揃っている
- human / yeast の両ケースで大きく破綻しない

## 補足

annotation は reporter UI の装飾ではなく、表示契約の基礎と考える。  
v0.5.0 ではここを正式に固定する。
