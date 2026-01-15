# Task Picker Agent

Cursor内の作業からタスクを拾い上げ、tasks.mdに追加するClaude Codeカスタムコマンド。

## 概要

このエージェントは以下のソースから情報を収集し、タスクを自動抽出します：

- **Claude Codeセッションログ** - セッション内のタスク（.md形式）
- **Git差分** - 変更されたファイルから作業内容を推測
- **プロジェクトドキュメント** - .md内のTODO/FIXME/未完了タスク

抽出されたタスクは `tasks.md` に追記され、後段の **Task Orchestration Agent** が深掘り・工数見積もりを行います。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                  Task Picker Agent                       │
│           Cursor内の作業からタスクを拾い上げる           │
├─────────────────────────────────────────────────────────┤
│  入力                                                    │
│  ├── Claude Codeセッションログ (.md)                    │
│  ├── Git差分（変更ファイル一覧）                        │
│  └── プロジェクト内ドキュメント (.md)                   │
├─────────────────────────────────────────────────────────┤
│  出力                                                    │
│  └── tasks.md（生のタスクリスト）                       │
├─────────────────────────────────────────────────────────┤
│  後段処理（別ツール）                                    │
│  └── Task Orchestration Agent                           │
│       ├── タスクの深掘り                                │
│       └── 工数見積もり                                  │
└─────────────────────────────────────────────────────────┘
```

## インストール

1. このリポジトリをクローン
```bash
git clone https://github.com/thedomainai/task-picker-agent.git
```

2. `.claude/commands/daily-tasks.md` をプロジェクトの `.claude/commands/` にコピー
```bash
mkdir -p .claude/commands
cp task-picker-agent/.claude/commands/daily-tasks.md .claude/commands/
```

3. 設定をカスタマイズ
   - `daily-tasks.md` 内のパスを自分の環境に合わせて変更
   - セッションログのパス
   - tasks.mdの出力先

## 使い方

Claude Codeで以下のコマンドを実行：

```
/daily-tasks
```

### フロー

1. **情報収集** - セッションログ、Git差分、ドキュメントを自動取得
2. **タスク抽出** - 各ソースからタスクを抽出
3. **確認** - ユーザーがタスク内容を確認・編集
4. **追記** - tasks.mdに追記

## 設定項目

| 項目 | デフォルト値 |
|------|-------------|
| セッションログ | `docs/01_resource/sessions/` |
| タスク出力先 | `docs/01_resource/tasks.md` |

## 必要環境

- [Claude Code](https://claude.ai/claude-code)

## ライセンス

MIT
