# 実装指示書: iwa-rnaseq-reporter v0.13.4
## タスク名
app.py 入口ロジックの薄化

## 対象 repo
iwa-rnaseq-reporter

## 対象 branch
dev-v0.13

---

## 0. このタスクの目的

v0.13.4 の目的は、現在 app.py の Input セクション周辺に残っている入口責務を、
**小さな helper / builder に寄せて、app.py を「処理する場所」から「読む場所」へ一段進めること**です。

今回の対象は、最低限以下です。

- input 文字列の受け取り後の入口フロー
- path 解決
- dataset load
- bundle ingest
- bundle diagnostic
- ReporterSessionContext 構築
- session_state への反映

重要:
- app.py 全面改造はしない
- PCA / Correlation / Gene Search / DEG には広げない
- loader / bundle_loader の本体責務は大きく変えない
- 巨大 controller / service 層は作らない

---

## 1. 今回やること

### 1-1. 入口処理を 1 本の helper に寄せる

Input セクションで現在段階的に行っている入口処理を、
**1 つの小さな orchestration helper** に寄せてください。

候補名:
- `load_reporter_entry_state(...)`
- `build_reporter_entry_state(...)`
- `run_reporter_entry_load(...)`

配置候補:
- `src/iwa_rnaseq_reporter/app/entry_loader.py`
- `src/iwa_rnaseq_reporter/app/entry_flow.py`

責務:
- user input string を受け取る
- path 解決を行う
- resolved input context を作る
- dataset load を試みる
- bundle ingest を試みる
- diagnostic を整える
- ReporterSessionContext を返す

返り値は、最低限以下のどちらかにしてください。

#### パターンA
`ReporterSessionContext` を返す

#### パターンB
`ReporterSessionContext` と、補助的な UI 用情報を返す

ただし、**UI 表示用の雑多な dict を大量に返さないこと**。

---

### 1-2. app.py では helper 呼び出しと描画に寄せる

`Load Dataset` ボタン押下後の app.py の役割を、最低限以下へ絞ってください。

- 空入力チェック
- helper 呼び出し
- session_state 保存
- success / error 表示
- context を使った描画

重要:
- app.py 側で path 解決ロジックを再実装しない
- app.py 側で context 組み立てを再実装しない
- app.py 側で bundle diagnostic 判定ロジックを増殖させない

---

### 1-3. session_state 更新を 1 箇所に寄せる

現在の入口処理で更新している session key 群が分散している場合、
それを **1 つの helper** に寄せてください。

候補名:
- `apply_reporter_session_context(...)`
- `sync_reporter_session_state(...)`

最低限同期対象:
- `reporter_session_context`
- `resolved_input_context`
- `dataset`
- `analysis_bundle`
- `analysis_bundle_diagnostic`

重要:
- downstream 互換のため既存 key は維持してよい
- ただし更新起点は 1 箇所へ寄せること
- stale state を起こしにくい更新順序にすること

---

### 1-4. Input セクションの責務を減らす

最終的に app.py の Input セクションが、概ね以下のような責務になる状態を目指してください。

- 入力受け取り
- ボタン押下判定
- 空入力時のエラー表示
- 入口 helper 呼び出し
- context の保存
- 最小限の通知表示

つまり、Input セクション内に

- path 判定分岐
- dataset load 分岐
- bundle ingest 分岐
- diagnostic 組み立て分岐
- session key ごとの細かい更新

が散らばらないようにしてください。

---

## 2. 今回やらないこと

以下は禁止です。

- app.py 全体の分割
- Section 8 以降の機能単位の再設計
- PCA / DEG など downstream state の再編
- loader / bundle_loader / legacy 層の全面改修
- ReporterSessionContext の巨大化
- ResultSpec / ReportPayloadSpec など schema 層の追加実装
- multi-use-case 展開
- telemetry / logging framework の導入

---

## 3. 設計方針

### 3-1. 入口 orchestration は薄く保つ
helper を作っても、それが巨大 service になっては意味がありません。
今回の helper は **入口処理をまとめるだけの薄い orchestration** に留めてください。

### 3-2. pure な処理と Streamlit 依存処理を分ける
可能な限り、

- pure な入口処理
- session_state 反映
- UI 表示

を分けてください。

理想:
- pure helper が ReporterSessionContext を返す
- Streamlit 側はそれを保存・表示するだけ

### 3-3. 既存責務を壊さない
- input resolution = path 解決
- resolved input context = 入口 metadata
- dataset = 解析実体
- analysis bundle = handoff metadata
- diagnostic = consume 視点の状態
- reporter session context = それらを束ねる薄い view

この責務分離は維持してください。

### 3-4. 既存 session key は互換性優先
downstream がまだ `dataset` などを直接参照しているはずなので、
今回の段では `reporter_session_context` を source of truth に寄せつつも、
既存 key の互換性は維持してください。

---

## 4. 実装の具体要件

### 4-1. helper の入力は単純にする
入口 orchestration helper の入力は、まずは

- `input_path_str: str`

程度で十分です。

必要なら内部で
- resolver
- dataset loader
- bundle loader
- diagnostic builder

を呼んでください。

### 4-2. helper の出力は ReporterSessionContext 中心
返り値はできるだけ `ReporterSessionContext` を中心にしてください。
複数の雑多な値を返す形は避けてください。

### 4-3. 失敗ケースを context で表現できるようにする
以下のケースを自然に扱えること。

- 入力は解決されたが dataset load に失敗
- dataset は load できたが bundle 失敗
- bundle は warning
- 未解決入力

### 4-4. success / failure 表示ルールは現状踏襲
今回の目的は UI 文言の刷新ではありません。
st.success / st.error / st.info などの使い方は、なるべく現状流儀を保ってください。

### 4-5. stale state を悪化させない
新しい load 試行時に、
前回の dataset / bundle / diagnostic が不自然に残ることを避けてください。

---

## 5. app.py への反映方針

### 5-1. Load Dataset ボタン押下時
以下のような主フローへ寄せてください。

1. 入力値確認
2. entry helper 呼び出し
3. ReporterSessionContext 取得
4. session_state へ反映
5. 必要なメッセージ表示

### 5-2. 描画側は session context を読む
Input Resolution Details や bundle summary は、
できるだけ `reporter_session_context` を起点に描画してください。

### 5-3. 既存 helper の扱い
`_try_load_bundle()` や `_render_bundle_summary()` など既存 helper を残してもかまいません。
ただし、可能であれば役割を見直し、

- `_try_load_bundle()` 相当の責務が entry helper に吸収される
- `_render_bundle_summary()` は context を読むだけ

に寄せてください。

---

## 6. テスト要件

最低限、以下を追加または更新してください。

### 6-1. entry helper 単体テスト
観点:
- 入力から ReporterSessionContext が返る
- dataset 成功 / bundle 成功
- dataset 成功 / bundle 失敗
- dataset 失敗
- unresolved input
が自然に表現される

### 6-2. session_state 同期 helper テスト
追加した場合のみ、
context から既存 session key 群へ正しく同期されることをテストしてください。

### 6-3. stale state 防止テスト
可能なら、
前回成功状態のあとに失敗ケースを流しても不自然な state が残りにくいことを確認してください。

### 6-4. 既存テストの通過
以下を壊さないこと。

- v0.13.1 の path 解決テスト
- v0.13.2 の resolved input context テスト
- v0.13.3 の reporter session context テスト
- integration test

---

## 7. 受け入れ基準

以下を満たしたら done 候補です。

- app.py の入口処理が小さな helper に寄っている
- path 解決 / dataset load / bundle ingest / diagnostic / session context 構築が app.py から多少薄くなっている
- session_state 更新が 1 箇所に寄っている
- app.py 側が context を読む形に一段進んでいる
- 既存 session key 互換を維持している
- downstream 機能へ影響を広げていない
- 既存テストが通っている

---

## 8. レビュー観点

セルフチェックで以下を確認してください。

- app.py の責務が減った
- helper が巨大 abstraction になっていない
- path 解決ロジックを再複製していない
- diagnostic 判定ロジックを再複製していない
- ReporterSessionContext の責務を壊していない
- Streamlit 依存処理と pure 処理の境界が以前より明確になった
- 下流 use-case に踏み込んでいない
- stale state が悪化していない

---

## 9. Gemini への注意

もし実装中に以下の問題が出たら、独断で広げずに報告してください。

- 入口 orchestration helper を作ると app.py の差分が逆に増える
- `_try_load_bundle()` や既存 helper の責務が中途半端に重複する
- session key の互換維持と単一更新点化が両立しにくい
- v0.13.5 の test 固定まで見ないと自然に閉じない

その場合は以下を明示してください。

- 今回スコープで自然にできる最小整理はどこまでか
- 何を v0.13.5 に送るべきか
- 妥協して残した重複は何か

---

## 10. 完了報告フォーマット

完了報告
タスク名: v0.13.4 app.py 入口ロジックの薄化
変更ファイル: <files>
実装要約: <何をしたか>
非変更範囲: <何を変えていないか>
テストコマンド: <commands>
テスト結果: <N passed>
懸念点: <あれば>
次の一手: <次タスク>
done 判定: <Yes / No>