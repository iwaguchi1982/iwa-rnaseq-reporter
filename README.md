# iwa-rnaseq-reporter

`iwa-rnaseq-reporter` は、RNA-Seq の結果を **見て、確認して、比較の準備をする** ための Web アプリです。  
`iwa-rnaseq-counter` で作成した結果を読み込み、サンプル構成・QC・発現量・比較したい群を、画面で順番に確認できることを重視しています。

このアプリは、いきなり複雑な統計設定を行うためのものではなく、  
まず **「結果を安全に見て、比較の前準備を進める」** ための入口として使えるようにする方針です。

---

## 1. このアプリでできること

- `iwa-rnaseq-counter` で作成した結果を読み込む
- サンプル一覧を確認する
- QC を確認する
- 発現量テーブルを確認する
- PCA や相関などの予備解析を確認する
- 比較したい群を整理する
- 比較条件に基づいて基本的な DEG 解析（統計的検定）を実行する
- DEGの変動解釈（Fold Changeの向きなど）を画面上で確認し、結果をCSVでダウンロードする

---

## 2. 想定ユーザー

このアプリは、特に次のような方を想定しています。

- Wet 実験が主な研究者
- Dry 解析の専門家ではないが、RNA-Seq 結果を確認したい人
- 解析担当者と相談しながら比較条件を整理したい人
- Web アプリで結果を確認したい人
- 納品前の確認や解析設計の下準備をしたい人

---

## 3. まずは Web アプリとして使う

まずは Web アプリとして使うことを想定しています。

```bash
pixi run streamlit run app.py
```
### Web アプリでの基本的な流れ
1. iwa-rnaseq-counter の結果を用意する
2. iwa-rnaseq-reporter で結果を読み込む
3. サンプル構成・QC・発現量を確認する
4. 比較したい群を整理する
5. 次の解析やレポート作成につなげる
### 最初に気にすればよいこと
まず利用時に気にすればよいのは次の点です。

- counter の結果を読み込めること
- サンプル一覧と QC を確認できること
- 発現量や予備解析を見られること
- 比較したい群を整理できること
- Web UI で段階的に進められること

内部の仕様は、使うだけなら意識しなくて大丈夫です。

## 4. 入力として用意するもの
通常は、iwa-rnaseq-counter が出力した結果を使います。
利用者目線では、まず次のどちらかがあれば使い始めやすい想定です。

- iwa-rnaseq-counter の出力フォルダ
- 必要な結果ファイルがまとまった結果フォルダ

必要に応じて、サンプル情報をまとめた CSV を使います。

### よく使う入力の例
- count データ
- サンプル一覧やサンプル情報
- QC 情報
- 比較したい群を整理するためのメタデータ

## 5. 何が見られるか
現段階では、主に次のものを確認できる想定です。

- サンプル一覧
- サンプルごとの情報
- QC 結果
- gene / transcript レベルの発現量テーブル
- PCA / 相関などの予備解析
- 比較対象の整理結果と基本 DEG 解析結果（変動の分かりやすさを重視したテーブルと、フルデータのCSVダウンロード）

## 6. このアプリの位置づけ
iwa-rnaseq-reporter は、iwa-rnaseq-counter の次に使うアプリです。

役割を一言でいうと、

- counter が「結果を作るアプリ」
- reporter が「結果を読んで確認し、比較の準備をするアプリ」

です。

つまり、RNA-Seq 解析の後半工程に入る前に、
##結果を見て、サンプルを確認し、比較の考え方を整理するための画面## と考えると分かりやすいです。

## 7. CLI について

このアプリは主に Web アプリとして使うことを想定しています。
CLI は、配線確認や開発中の確認、もしくは結果を機械的に処理したい場合に使います。

現時点では、まず Web UI を主役として考えてください。

## 8. 今後の拡張イメージ

今後は、段階的に次のような方向へ広げていく予定です。

- 比較条件の拡張
- report export の強化
- comparator との連携
- signature scorer との連携
- report automation との接続

## 9. 開発者向けメモ

ここから下は、将来の自分向けの短いメモです。
利用だけが目的なら読まなくて大丈夫です。

## 9.1 現在の役割

iwa-rnaseq-reporter は RNA-Seq Suite における 確認・比較設計・解析入口 のアプリ。

## 9.2 現在の大まかな流れ

内部では、おおまかに次の順で処理する。

- 結果を読む
- 比較対象を決める
- 解析を実行する
- 出力を書き出す

## 9.3 いま大事にしていること
- comparison 解決を処理本体から分ける
- counter -> reporter の接続を先に固める
- README に Spec の説明を出しすぎない
- 共通仕様に腫瘍専用語を入れすぎない

## 9.4 入力の考え方

表向きには「counter の結果を読むアプリ」として見せる。
内部では、比較条件やサンプル情報を使って比較対象を解決する。

## 9.5 今後の拡張候補
- sample selector の拡張
- paired design の強化
- covariate 対応
- comparator 連携
- signature scorer 連携
- report export 強化

## License

This repository is distributed under the Iwa Collections Non-Resale License 1.0.
Commercial resale of the software itself, or paid redistribution of derivative versions where the software is the primary value, is prohibited.

本リポジトリは Iwa Collections Non-Resale License 1.0 で公開しています。
ソフトウェア自体の有償販売、および本ソフトウェアが主たる価値となる派生物の有償再配布は禁止です。