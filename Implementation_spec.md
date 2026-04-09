# 実装指示書: iwa-rnaseq-reporter v0.13.2
## タスク名
Resolved Input Context の導入

## 対象 repo
iwa-rnaseq-reporter

## 対象 branch
dev-v0.13
全ての試験をパスした場合はdev-v0.13にPushしてください。

---

## 0. このタスクの目的

v0.13.2 の目的は、v0.13.1 で導入した Input / manifest 解決結果を、
app.py の局所変数や一時分岐としてではなく、
**意味のある軽い context 構造**として扱えるようにすることです。

今回の段階では、まだ Reporter 全体の Session Context は作りません。

このタスクでやるのはあくまで以下です。

- v0.13.1 の解決結果を `ResolvedInputContext` として保持できるようにする
- `st.session_state` に入口 metadata を安定して載せられるようにする
- app.py の Input セクションが context を読む側へ少し寄るようにする
- 入口 metadata の表示を context 起点に整理する
- 次段 v0.13.3 の `ReporterSessionContext` 導入を邪魔しない形に留める

---

## 1. 今回やること

### 1-1. Resolved Input Context を追加する

新規に、v0.13.1 の `InputResolutionResult` を app/session で扱うための
軽い dataclass を追加してください。

推奨名:
- `ResolvedInputContext`

配置候補:
- `src/iwa_rnaseq_reporter/app/resolved_input_context.py`

もしくは repo 構造上自然なら
- `src/iwa_rnaseq_reporter/app/session_context.py`

でもよいですが、
**今回は巨大な session manager を作らず、Resolved Input 専用責務に留めること**。

最低限持たせる項目:

- `original_input_path: str`
- `normalized_input_path: str`
- `resolved_dataset_manifest_path: str | None`
- `resolved_bundle_manifest_path: str | None`
- `input_kind: str`
- `load_mode: str`
- `resolution_messages: tuple[str, ...] | list[str]`

必要なら以下を追加してよいです。

- `has_dataset_manifest: bool` 相当の property
- `has_bundle_manifest: bool` 相当の property
- `is_unresolved: bool` 相当の property

ただし、**dataset / bundle / diagnostic 自体はここに入れないこと**。

---

### 1-2. InputResolutionResult からの変換を 1 箇所で定義する

以下のどちらかの形で、
v0.13.1 の解決結果から `ResolvedInputContext` を作る変換を定義してください。

候補:
- `ResolvedInputContext.from_resolution_result(...)`
- `build_resolved_input_context(...)`

重要:
- source of truth はあくまで `resolve_reporter_input_paths(...)`
- path 解決ロジックを再実装しない
- 単なる詰め替えではなく、app/session で扱いやすい read-only view にする

この変換は **pure** にしてください。
Streamlit に直接依存しないこと。

---

### 1-3. app.py で resolved_input_context を session_state に保存する

`Load Dataset` 実行時の流れを、最低限以下の順に寄せてください。

1. ユーザー入力を受け取る
2. `resolve_reporter_input_paths(...)` で解決する
3. その結果から `ResolvedInputContext` を生成する
4. `st.session_state["resolved_input_context"]` に保存する
5. その後に dataset load / bundle ingest を行う

重要:
- dataset load 成否に関係なく、**非空入力で解決できた内容は context として残す**
- dataset load が失敗しても、入口解決結果の表示は可能にする
- 空入力時の扱いは repo の既存流儀に合わせてよいが、stale な context を残し続けないこと

---

### 1-4. app.py は context を読む側に少し寄せる

v0.13.1 で追加した Input Resolution Details 相当の UI がある場合、
その表示は ad-hoc な local 変数や resolution result 直接表示ではなく、
**`resolved_input_context` を読む形**へ寄せてください。

最低限表示したい項目:

- Original Input
- Normalized Input
- Resolved Dataset Manifest
- Resolved Bundle Manifest
- Input Kind
- Load Mode
- Resolution Messages

ただし今回は UI 改修が主目的ではないので、
**見た目の刷新は不要**です。

---

## 2. 今回やらないこと

このタスクでは以下はやらないでください。

- `ReporterSessionContext` の本格導入
- `dataset / analysis_bundle / analysis_bundle_diagnostic` を 1 つに束ねること
- session manager / state manager の導入
- app.py 全面書き換え
- Section 8 以降の下流 use-case 改修
- PCA / Correlation / Gene Search / DEG への追加接続
- bundle summary UI の再設計
- loader / bundle_loader の本体再設計
- Counter 側 contract の変更

---

## 3. 設計方針

### 3-1. 今回の context は「入口 metadata 専用」
この context は、
dataset や bundle 本体ではなく、
**「何をどう解決してこの load に入ったか」** を表すためのものです。

### 3-2. dataset / bundle / diagnostic と混ぜない
責務は必ず分けてください。

- resolved input context = 入口 metadata
- dataset = 解析実体
- analysis_bundle = handoff metadata
- analysis_bundle_diagnostic = consume 視点の状態

### 3-3. session_state に置くが、構造は pure に保つ
保存先は `st.session_state` でよいですが、
context そのものは Streamlit 非依存の dataclass にしてください。

### 3-4. source of truth は v0.13.1 の resolver
`ResolvedInputContext` の値は
`resolve_reporter_input_paths(...)` の結果に従うこと。
app.py 側で別分岐を増やさないでください。

### 3-5. v0.13.3 を先食いしない
次段で `ReporterSessionContext` を作る前提なので、
今回の context は **軽く独立した部品**に留めてください。

---

## 4. 実装の具体要件

### 4-1. dataclass を優先
`ResolvedInputContext` は dataclass を優先してください。

### 4-2. Path は str ベースでよい
既存実装との整合がよければ内部で `Path` を使ってもよいですが、
context の公開フィールドは `str | None` ベースで問題ありません。

### 4-3. property は最小限
便利 property を追加してもよいですが、
以下程度に留めてください。

例:
- `has_dataset_manifest`
- `has_bundle_manifest`
- `is_unresolved`

### 4-4. デバッグ表示用 helper は許容
UI 表示のために、たとえば

- `to_display_dict()`
- `to_debug_rows()`

のような helper を追加してもよいです。
ただし表示整形責務を盛りすぎないこと。

### 4-5. session key を固定する
以下の key を推奨します。

- `st.session_state["resolved_input_context"]`

名前を変える場合は、
今後 `ReporterSessionContext` に統合しやすいことを優先してください。

---

## 5. app.py への反映方針

### 5-1. Load Dataset 実行時
最低限以下の形に整理してください。

- input string を受け取る
- resolver を呼ぶ
- resolved input context を作る
- session に保存する
- dataset load を `resolved_dataset_manifest_path` 優先で行う
- bundle ingest を `resolved_bundle_manifest_path` 優先で行う

### 5-2. load failure 時
dataset load が失敗しても、
`resolved_input_context` は残してよいです。
入口がどう解決されたかをユーザーが見られる方が自然です。

### 5-3. empty input 時
空入力時は repo の既存 UX を維持してよいですが、
前回の resolved context を誤って残し続けないようにしてください。

### 5-4. 既存 keys は壊さない
今回の段階では、少なくとも以下の既存 state は壊さないこと。

- `dataset`
- `analysis_bundle`
- `analysis_bundle_diagnostic`

今回は新たに `resolved_input_context` を追加するだけに近いイメージで進めてください。

---

## 6. テスト要件

最低限、以下のテストを追加してください。

### 6-1. context 変換 test
観点:
- `InputResolutionResult` から `ResolvedInputContext` が期待通りに作られる
- original / normalized / resolved paths / kind / mode / messages が保持される

### 6-2. unresolved context test
観点:
- 未解決ケースでも context が作れる
- `resolved_dataset_manifest_path is None`
- `resolved_bundle_manifest_path is None`
- `is_unresolved` 相当が自然に扱える

### 6-3. context property test
観点:
- `has_dataset_manifest`
- `has_bundle_manifest`
- `is_unresolved`
などを持たせた場合、それが期待通り動く

### 6-4. display helper test
表示用 helper を追加した場合のみ、
その出力が UI 前提で崩れにくいことをテストしてください。

### 6-5. app integration の最小確認
観点:
- `resolved_input_context` を導入しても v0.13.1 の path 解決テストが壊れない
- 既存 integration test が通る
- v0.12 の initial handoff surface を壊していない

---

## 7. 受け入れ基準

以下を満たしたら、このタスクは done 候補です。

- `ResolvedInputContext` が追加されている
- v0.13.1 の解決結果から context を作る pure な変換がある
- `st.session_state["resolved_input_context"]` に入口 metadata を保持できる
- Input Resolution Details 相当の表示が context を読む形になっている
- dataset / bundle / diagnostic をまだ混ぜていない
- app.py の差分が Input セクション周辺に留まっている
- v0.13.1 の path 解決 tests を壊していない
- 既存 integration tests が通っている

---

## 8. レビュー観点

セルフチェックで以下を確認してください。

- source of truth を resolver に一本化した
- path 解決ロジックを app.py へ再複製していない
- `ResolvedInputContext` に dataset / bundle / diagnostic を入れていない
- Streamlit 依存を context 本体へ持ち込んでいない
- Input セクションの責務だけを整理した
- UI のためだけの過剰 abstraction を作っていない
- v0.13.3 の ReporterSessionContext を先食いしていない
- 既存 public API を壊していない
- 例外を握りつぶしていない

---

## 9. Gemini への注意

もし実装中に以下の問題が出たら、
大きく広げずに報告してください。

- `InputResolutionResult` と `ResolvedInputContext` の責務差が薄すぎる
- `resolved_input_context` を入れるだけでは app.py 側の分岐整理が不十分
- 実質的に `ReporterSessionContext` まで進めないと不自然になる
- session_state の更新順序を変えると既存 use-case に影響が出る

その場合は以下を明示してください。

- 何が詰まっているか
- 今回スコープでどこまでなら自然か
- v0.13.2 として成立する最小代替案は何か
- v0.13.3 に送るべき論点は何か

---

## 10. 完了報告フォーマット

完了報告
タスク名: v0.13.2 Resolved Input Context の導入
変更ファイル: <files>
実装要約: <何をしたか>
非変更範囲: <何を変えていないか>
テストコマンド: <commands>
テスト結果: <N passed>
懸念点: <あれば>
次の一手: <次タスク>
done 判定: <Yes / No>