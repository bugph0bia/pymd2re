pymd2re
===

![Software Version](http://img.shields.io/badge/Version-v0.1.0-green.svg?style=flat)
![Python Version](http://img.shields.io/badge/Python-3.6-blue.svg?style=flat)
[![MIT License](http://img.shields.io/badge/license-MIT-blue.svg?style=flat)](LICENSE)

## 概要
MarkdownファイルをRe:VIEWファイルに変換するスクリプト

## バージョン
v0.1.0

## 動作環境
- Python 3.6以上
- 標準ライブラリ以外の依存ライブラリは無し

## ライセンス
MIT License

## 制限事項
- 同一行に複数種類のブロックが存在するケースは不可
    - 行の途中から複数行コメントが始まるなど
    - 同一行に複数種類のインライン要素は許可
- 以下には未対応（順次対応したい）。
    - コードブロックの言語名の取得（無視する）
    - 外部参照リンク
        - あらかじめリンクを定義して複数回記述する書き方のこと
    - 文書内の見出しへのリンク
    - 表内の列のアライメント指定の取得
    - チェックリストのチェックON/OFFの取得
    - マークダウン記号のエスケープ

## メモ
- 構文解析は正規表現の力技で実装した。
- 文書構造を中間表現で保持する方式。
- レンダラを用意すれば、Re:VIEW以外のフォーマットへの出力も可能になる
