# 実装指示書: iwa-rnaseq-reporter v0.13.5
## タスク名
入口状態 tests の固定

## 対象 repo
iwa-rnaseq-reporter

## 対象 branch
dev-v0.13

---

## 0. このタスクの目的

v0.13.5 の目的は、v0.13.1〜v0.13.4 で導入した入口整理の構造を、
今後の局所修正や app.py 側の微調整で壊れにくくするために、
**tests を追加・整理して entry-state surface を固定すること**です。

今回の対象は、最低限以下です。

- input / manifest 解決
- ResolvedInputContext
- ReporterSessionContext
- entry_loader
- session state 同期
- dataset-only fallback
- unresolved input
- bundle warning / error の入口表現

重要:
- このタスクは原則 **テスト中心** です
- 新しい機能追加はしない
- app.py 全面改造はしない
- 下流機能（PCA / DEG など）には広げない
- helper の責務を広げない

---

## 1. 今回やること

### 1-1. 入口状態のテスト観点を明文化して追加する

v0.13 で整えた入口状態を、以下の観点で固定してください。

#### A. input resolution surface
- original input
- resolved dataset manifest
- resolved bundle manifest
- input_kind
- load_mode
- resolution_messages

#### B. resolved input context surface
- InputResolutionResult からの変換
- property の挙動
- display 用辞書 / rows の安定性（ある場合）

#### C. reporter session context surface
- resolved_input_context / dataset / bundle / diagnostic の保持
- partial state の表現
- convenience property の挙動

#### D. entry loader surface
- 入力から ReporterSessionContext が返る
- dataset 成功 / bundle 成功
- dataset 成功 / bundle warning or error
- dataset 失敗
- unresolved input

#### E. session sync surface
- ReporterSessionContext から既存 session key 群へ同期される
- stale state を起こしにくい
- 互換 key が意図通り更新される

---

### 1-2. 既存テストを整理し、重複を最小化する

すでに追加済みの以下の系統がある前提です。

- `tests/io/test_input_resolution.py`
- `tests/app/test_resolved_input_context.py`
- `tests/app/test_reporter_session_context.py`
- `tests/app/test_entry_loader.py`

今回はこれらを踏まえて、
**どのファイルが何の surface を守るのかが明確になるように整理**してください。

重要:
- 同じ観点の重複テストを無駄に増やさない
- ただし「境界」を守るための重なりは許容
- unit / entry-flow / integration の責務を混ぜない

---

### 1-3. dataset-only fallback を明示的に固定する

v0.13 系で重要なのは、
**bundle がなくても dataset-only で継続できること** です。

これを明示的にテストで固定してください。

最低限確認したいこと:
- bundle manifest が解決できなくても dataset load が通るなら継続できる
- ReporterSessionContext 上で dataset は available、bundle は unavailable と表現される
- diagnostic が warning / error でも app が致命停止前提にならない
- 既存 integration surface を壊していない

---

### 1-4. unresolved / failure 系を固定する

入口整理で壊れやすいのは failure 系です。
以下を優先的に固定してください。

- 入力パスが不正 / 未解決
- resolved input はあるが dataset load 失敗
- dataset は成功したが bundle ingest 失敗
- bundle が warning 状態
- session sync 後に古い成功状態が不自然に残らない

---

### 1-5. session_state 同期の回帰を防ぐ

`sync_reporter_session_state(...)` 相当がある前提で、
以下をテストで固定してください。

最低限確認したい session key:
- `reporter_session_context`
- `resolved_input_context`
- `dataset`
- `analysis_bundle`
- `analysis_bundle_diagnostic`

観点:
- context から期待通りに同期される
- bundle failure 時に以前の bundle が残りにくい
- dataset failure 時に以前の dataset が残るなら、その挙動が明示的である
- 少なくとも「意図せず古い成功結果が残る」ことを防ぐ

---

## 2. 今回やらないこと

以下は禁止です。

- 新しい app 機能の追加
- app.py の再リファクタ
- loader / bundle_loader の本体仕様変更
- input resolution アルゴリズムの拡張
- ReporterSessionContext の新責務追加
- 下流ページの state 再設計
- UI デザイン調整
- Counter 側 contract の変更
- テスト都合だけの大規模設計変更

---

## 3. 設計方針

### 3-1. テスト対象は「入口状態 surface」
今回固定したいのは内部実装ではなく、
**外から見た入口状態の契約**です。

つまり、以下が守られていればよいです。

- 何を入力とみなすか
- 何を解決結果とみなすか
- dataset / bundle / diagnostic をどう束ねるか
- failure / fallback をどう表現するか
- session にどう反映するか

### 3-2. unit / flow / integration を分ける
テストはなるべく次の3層に分けてください。

#### unit
- input resolution
- context model
- session sync helper

#### flow
- entry_loader が返す ReporterSessionContext

#### integration
- Counter -> Reporter handoff の既存面
- 入口整理後も initial handoff surface が壊れていないこと

### 3-3. brittle な文言完全一致は避ける
`resolution_messages` や UI 用表示辞書については、
必要以上に全文一致に縛らず、
**意図が保たれていること** を確認する形を優先してください。

### 3-4. stale state 観点を重視する
入口 state 整理では、
新規成功ケースよりも **前回 state の残留** が事故になりやすいです。
この観点を軽視しないでください。

---

## 4. 実装の具体要件

### 4-1. 追加してよいテストファイル
必要なら以下に追加してよいです。

- `tests/io/test_input_resolution.py`
- `tests/app/test_resolved_input_context.py`
- `tests/app/test_reporter_session_context.py`
- `tests/app/test_entry_loader.py`
- `tests/app/test_session_state_sync.py`（必要なら新規）

ただし、責務が明確ならファイル分割は増やしてよいです。

### 4-2. fixture は最小限
fixture は既存のものを活用し、
このタスクのためだけに巨大 fixture 群を増やしすぎないこと。

### 4-3. monkeypatch / stub は許容
entry_loader のテストでは、
dataset loader / bundle loader の挙動を局所的に固定するための
monkeypatch や stub は許容です。

ただし、
**実際の public API 契約を壊すようなモック** は避けてください。

### 4-4. テスト名は観点が分かるものにする
例:
- `test_resolve_paths_falls_back_to_dataset_only_when_bundle_missing`
- `test_reporter_session_context_marks_bundle_error_without_dataset_loss`
- `test_sync_reporter_session_state_clears_stale_bundle_state`

のように、何を守るテストかが名前で分かるようにしてください。

---

## 5. 最低限追加・強化したいテスト観点

### 5-1. input resolution
- dataset manifest 入力
- bundle manifest 入力
- directory 入力
- unresolved input
- bundle missing -> dataset_only

### 5-2. ResolvedInputContext
- from_resolution_result
- `has_dataset_manifest`
- `has_bundle_manifest`
- `is_unresolved`
- display helper（あれば）

### 5-3. ReporterSessionContext
- fully populated
- dataset only
- bundle warning
- bundle error
- resolved input only

### 5-4. entry_loader
- success path
- dataset-only fallback
- dataset load failure
- unresolved input
- warning / error propagation

### 5-5. session sync
- all keys updated
- stale bundle cleared
- stale diagnostic cleared
- legacy keys kept compatible

### 5-6. integration
- 既存 `test_counter_reporter_handoff.py` が通る
- v0.12 で作った initial handoff surface が壊れていない

---

## 6. 受け入れ基準

以下を満たしたら done 候補です。

- v0.13 系の入口整理を守るテスト群が揃っている
- input resolution / context / entry loader / session sync の責務がテスト上で分かれている
- dataset-only fallback が明示的に固定されている
- unresolved / failure 系が固定されている
- stale state 系の回帰防止テストがある、または既存テストで十分に担保されている
- 既存 integration test を壊していない
- 新機能追加なしで test hardening に集中している

---

## 7. レビュー観点

セルフチェックで以下を確認してください。

- テストが内部実装に過剰依存していない
- 同じ観点の重複テストを増やしすぎていない
- failure / fallback を十分に見ている
- dataset-only 継続の契約を固定できている
- session sync の stale state 観点を押さえている
- integration surface を壊していない
- 新機能を混ぜていない
- 今回の差分が test hardening 中心に留まっている

---

## 8. Gemini への注意

もし実装中に以下の問題が出たら、独断で仕様変更せずに報告してください。

- stale state の正しい期待値が現状コードから読み取りにくい
- session sync の現挙動と理想挙動にズレがある
- entry_loader のモックテストだけでは信頼性が足りない
- integration test 側の fixture が入口整理を十分に表現できない

その場合は以下を明示してください。

- どの挙動が曖昧か
- 現状コードはどう動くか
- 今回は何を固定し、何を次タスクへ送るべきか
- 仕様として先に決めるべき論点は何か

---

## 9. 完了報告フォーマット

完了報告
タスク名: v0.13.5 入口状態 tests の固定
変更ファイル: <files>
実装要約: <何をしたか>
非変更範囲: <何を変えていないか>
テストコマンド: <commands>
テスト結果: <N passed>
懸念点: <あれば>
次の一手: <次タスク>
done 判定: <Yes / No>