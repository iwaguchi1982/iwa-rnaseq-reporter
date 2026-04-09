# 実装指示書: iwa-rnaseq-reporter v0.13.3
## タスク名
Reporter Session Context の導入

## 対象 repo
iwa-rnaseq-reporter

## 対象 branch
dev-v0.13

---

## 0. このタスクの目的

v0.13.3 の目的は、v0.13.1 と v0.13.2 で整えた入口状態を、
app.py 内の散在した `st.session_state` キーの寄せ集めとしてではなく、
**意味のある軽い Reporter Session Context** として扱えるようにすることです。

このタスクで整理対象にするのは、最低限以下です。

- resolved_input_context
- dataset
- analysis_bundle
- analysis_bundle_diagnostic

重要:
- これは **Reporter 全体の巨大 state manager** を作るタスクではありません
- これは **Input セクション周辺の入口状態を整えるタスク** です
- PCA / Correlation / Gene Search / DEG などの downstream 機能は触りません
- app.py の全面改造はしません

---

## 1. 今回やること

### 1-1. ReporterSessionContext を追加する

新規に、入口状態を束ねる軽い dataclass を追加してください。

推奨名:
- `ReporterSessionContext`

推奨配置:
- `src/iwa_rnaseq_reporter/app/reporter_session_context.py`

最低限持たせる項目:

- `resolved_input_context: ResolvedInputContext | None`
- `dataset: object | None`
- `analysis_bundle: ReporterAnalysisBundle | None`
- `analysis_bundle_diagnostic: BundleDiagnostic | None`

型は repo の既存構造に合わせて具体化してよいですが、
**今回の context は app が入口状態を読むための薄い構造** に留めてください。

必要なら以下のような便利 property を追加してよいです。

- `has_resolved_input`
- `has_dataset`
- `has_analysis_bundle`
- `has_bundle_diagnostic`
- `is_dataset_ready`
- `is_bundle_ready`
- `is_dataset_only_mode`
- `is_bundle_warning`
- `is_bundle_error`

ただし、便利 property は増やしすぎないこと。

---

### 1-2. context 生成 / 更新 helper を追加する

以下のどちらかの方向で、pure な builder / updater を追加してください。

候補:
- `build_reporter_session_context(...)`
- `ReporterSessionContext.from_parts(...)`
- `update_reporter_session_context(...)`

推奨責務:
- `resolved_input_context`
- `dataset`
- `analysis_bundle`
- `analysis_bundle_diagnostic`

を受け取り、`ReporterSessionContext` を返す。

重要:
- context 内で dataset load を実行しない
- context 内で bundle ingest を実行しない
- context は状態を表す object であり、処理本体は持たない
- Streamlit に直接依存しない pure 実装にする

---

### 1-3. app.py の入口 state を ReporterSessionContext に寄せる

`Load Dataset` 実行時の入口フローを、最低限以下の流れへ寄せてください。

1. user input を受け取る
2. `resolve_reporter_input_paths(...)` を呼ぶ
3. `ResolvedInputContext` を作る
4. dataset load を試みる
5. bundle ingest を試みる
6. 上記結果から `ReporterSessionContext` を作る
7. `st.session_state["reporter_session_context"]` に保存する

重要:
- 今回の段では、既存の
  - `dataset`
  - `analysis_bundle`
  - `analysis_bundle_diagnostic`
  - `resolved_input_context`
  を即完全廃止してもよいとは限りません
- downstream 互換性を保つため、必要であれば既存キーも並行保持してかまいません
- ただし **app.py の表示や分岐は、できるだけ `reporter_session_context` を読む形へ寄せる** こと

---

### 1-4. Input / Load 周辺 UI を session context 起点に整理する

現在 app.py にある入口表示や初期 summary があれば、
それを ad-hoc な session key 群ではなく、
**`reporter_session_context` を読む形** へ少し寄せてください。

今回の対象はあくまで入口周辺です。

最低限整理したい対象:
- Input Resolution Details
- Load 成否に関わる入口状態表示
- bundle summary / diagnostic の参照起点

ここでのゴールは UI 改修ではなく、
**表示が context を source of truth として読めること** です。

---

## 2. 今回やらないこと

このタスクでは以下は禁止です。

- app.py の全面再設計
- PCA / Correlation / Gene Search / DEG の state 管理変更
- session manager / controller の大型導入
- dataset loader / bundle loader の本体再設計
- Counter 側 contract の変更
- bundle ingest の責務再分離の大改造
- Section 8 以降の機能追加
- multi-use-case 展開
- telemetry / monitoring の導入

---

## 3. 設計方針

### 3-1. context は「入口状態の束ね」に限定する
この context は、
Reporter 全体の万能 state object ではなく、
**入口で今何が解決され、何が読み込まれ、bundle consume がどう見えているか**
をまとめるためのものです。

### 3-2. dataset / bundle / diagnostic の責務は混ぜない
context は束ねるだけで、意味は分離したままにしてください。

- resolved_input_context = 入口 metadata
- dataset = 解析実体
- analysis_bundle = handoff metadata
- analysis_bundle_diagnostic = consume 視点の状態

### 3-3. pure dataclass を優先する
session に保存する先は Streamlit でよいですが、
context 本体は pure な dataclass としてください。

### 3-4. app.py は context を読む側へ寄せる
今回の主眼は、
`st.session_state["dataset"]` などを散発的に直読む構造から、
入口周辺だけでも `reporter_session_context` 起点に揃えることです。

### 3-5. v0.13.4 を先食いしすぎない
app.py の薄化は次段でも行います。
今回は **context 導入で自然になる範囲まで** に留めてください。

---

## 4. 実装の具体要件

### 4-1. dataclass を優先
`ReporterSessionContext` は dataclass を優先してください。

### 4-2. None を明示的に扱える構造にする
以下のような partial state を自然に持てるようにしてください。

例:
- resolved input はあるが dataset は未 load
- dataset はあるが bundle はない
- bundle はあるが diagnostic は warning
- dataset load failed だが resolved input は残る

### 4-3. helper / property は最小限
便利 property を追加してもよいですが、
責務の説明を超えてロジックを持ちすぎないこと。

### 4-4. context を dict の寄せ集めにしない
明示的なフィールドを持つ dataclass にしてください。
将来の v0.13.4 以降で読みやすさを保つためです。

### 4-5. 既存 state との互換性を壊しすぎない
downstream 側がまだ `dataset` 直参照をしているはずなので、
この段階では互換性維持を優先してください。

---

## 5. app.py への反映方針

### 5-1. Load Dataset の主フロー
最低限、以下の情報を 1 回の load 試行ごとに context 化してください。

- 解決された入力情報
- dataset load の結果
- bundle ingest の結果
- bundle diagnostic

### 5-2. load 成否と context 更新
以下のケースを自然に表現できるようにしてください。

#### ケースA
resolved input あり / dataset 成功 / bundle 成功  
→ fully populated に近い context

#### ケースB
resolved input あり / dataset 成功 / bundle 失敗  
→ dataset はあるが bundle diagnostic は error または warning

#### ケースC
resolved input あり / dataset 失敗  
→ resolved_input_context は残るが dataset は None

#### ケースD
未入力または未解決  
→ context は None または unresolved 状態として扱う

### 5-3. 既存 helper の扱い
`_try_load_bundle()` などの既存 helper を使うのはかまいませんが、
その結果を最終的に `ReporterSessionContext` に反映してください。

### 5-4. 表示起点
入口周辺の表示はできるだけ

- `session_ctx = st.session_state.get("reporter_session_context")`

のように受けて、
そこから読む形に寄せてください。

---

## 6. テスト要件

最低限、以下のテストを追加してください。

### 6-1. ReporterSessionContext 生成 test
観点:
- resolved_input_context / dataset / bundle / diagnostic を与えると
  期待通りの context が作られる

### 6-2. partial state test
観点:
- dataset のみ
- dataset + bundle
- resolved_input のみ
- resolved_input + diagnostic error
などの partial state が自然に扱える

### 6-3. property test
便利 property を追加した場合、
以下が直感通り動くことをテストしてください。

例:
- `has_dataset`
- `has_analysis_bundle`
- `is_dataset_only_mode`
- `is_bundle_warning`
- `is_bundle_error`

### 6-4. app integration の最小確認
観点:
- `reporter_session_context` を導入しても
  既存の path 解決 test が壊れない
- v0.13.2 の resolved_input_context test が壊れない
- 既存 integration test が通る
- v0.12 の initial handoff surface を壊していない

### 6-5. stale state 防止の確認
可能なら以下もテストしてください。
- 新しい load 試行時に古い bundle / diagnostic が不自然に残らない
- dataset failure 時に前回成功分が誤表示されにくい

---

## 7. 受け入れ基準

以下を満たしたら、このタスクは done 候補です。

- `ReporterSessionContext` が追加されている
- resolved_input_context / dataset / analysis_bundle / analysis_bundle_diagnostic を束ねられる
- context 生成が pure な helper / classmethod で定義されている
- `st.session_state["reporter_session_context"]` に入口状態を保持できる
- app.py の入口周辺が context を読む形に少し寄っている
- dataset / bundle / diagnostic の責務を混ぜていない
- v0.13.1 / v0.13.2 のテストを壊していない
- 既存 integration test が通っている

---

## 8. レビュー観点

セルフチェックで以下を確認してください。

- ReporterSessionContext が巨大 abstraction になっていない
- dataset / bundle / diagnostic の意味を壊していない
- resolved_input_context の責務を維持している
- app.py に state 分岐を再増殖させていない
- Streamlit 依存を context 本体に持ち込んでいない
- 既存 public API を壊していない
- Input セクション周辺の整理に留めた
- downstream 機能へ広げていない
- stale state が以前より悪化していない

---

## 9. Gemini への注意

もし実装中に以下の問題が出たら、
独断で大きく広げずに報告してください。

- ReporterSessionContext を入れても app.py 側の整理効果が薄い
- 既存 helper の返り値設計が session context と噛み合わない
- 古い session key 群との二重管理が不自然になる
- v0.13.4 の薄化までやらないと設計が閉じない

その場合は以下を明示してください。

- 今回スコープでどこまでなら自然か
- どこからが v0.13.4 に送るべき論点か
- 既存互換性維持のために残した妥協点は何か

---

## 10. 完了報告フォーマット

完了報告
タスク名: v0.13.3 Reporter Session Context の導入
変更ファイル: <files>
実装要約: <何をしたか>
非変更範囲: <何を変えていないか>
テストコマンド: <commands>
テスト結果: <N passed>
懸念点: <あれば>
次の一手: <次タスク>
done 判定: <Yes / No>