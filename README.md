# Task Picker Agent

日々の会議やGit作業から自動的にタスクを抽出し、Notionのチケット_DBに登録するClaude Codeカスタムコマンド。

## 概要

このエージェントは以下のソースから情報を収集し、タスクを自動抽出します：

- **議事録_DB** - Notionの会議議事録
- **ドキュメント_DB** - 最近編集されたドキュメント
- **Git履歴** - 今日のコミット履歴

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
   - `daily-tasks.md` 内のNotion データベースIDを自分の環境に合わせて変更
   - 責任者のユーザーIDを更新

## 使い方

Claude Codeで以下のコマンドを実行：

```
/daily-tasks
```

### フロー

1. **情報収集** - 議事録、ドキュメント、Gitコミットを自動取得
2. **タスク案提示** - 収集した情報からタスク一覧を作成
3. **確認** - ユーザーがタスク内容を確認・編集
4. **登録** - Notionのチケット_DBに自動登録

## 設定項目

| 項目 | 説明 |
|------|------|
| `議事録_DB ID` | Notionの議事録データベースID |
| `ドキュメント_DB ID` | NotionのドキュメントデータベースID |
| `チケット_DB data_source_id` | タスク登録先のデータソースID |
| `責任者ID` | デフォルトの担当者ユーザーID |

## 必要環境

- [Claude Code](https://claude.ai/claude-code)
- Notion MCP連携が設定済みであること

## ライセンス

MIT
