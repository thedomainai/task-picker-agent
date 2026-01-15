# 日次タスク登録コマンド

このコマンドは、今日の会議やGitでの作業を確認し、チケット_DBにタスクを登録します。

## 実行手順

### 1. 今日の日付を確認
今日の日付: $CURRENT_DATE

### 2. 情報収集

以下の情報を順番に収集してください：

#### 2.1 議事録_DB から最近の会議を取得
Notion fetchツールで議事録_DBを取得し、今日（または指定日）の会議を確認：
```
notion-fetch: 2b0a6623cccd80d6ab49e255177b0136
```

#### 2.2 ドキュメント_DB から最近編集されたドキュメントを確認
Notion fetchツールでドキュメント_DBを取得：
```
notion-fetch: 2b0a6623cccd801284cef87f90c5f8ea
```

#### 2.3 Git履歴から今日のコミットを取得
ワークスペース内の全リポジトリから今日のコミットを検索：
```bash
find ~/workspace -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  commits=$(git -C "$repo" log --oneline --since="today 00:00" 2>/dev/null)
  if [ -n "$commits" ]; then
    echo "=== $repo ==="
    echo "$commits"
  fi
done
```

#### 2.4 追加タスクの確認
ユーザーに「今日行った他の作業や、登録したいタスクはありますか？」と質問

### 3. タスク案の作成

収集した情報から、以下の形式でタスク案を作成してユーザーに提示：

| # | タイトル | ステータス | 期日 | 見積（h） |
|---|----------|------------|------|-----------|
| 1 | [タスク名] | 未着手/完了 | [日付] | [時間] |

**ステータス候補**: 未着手, ToDo, 進行中, レビュー, 一時停止, 完了, 中止

### 4. チケット_DBへの登録

ユーザー確認後、Notion create-pages ツールで登録：

- **data_source_id**: `2b0a6623-cccd-8095-8aa4-000b6ee76f6b`
- **責任者ID**: `2b0d872b-594c-8107-b070-0002ce42d546` (中林)

登録例：
```json
{
  "parent": {"data_source_id": "2b0a6623-cccd-8095-8aa4-000b6ee76f6b"},
  "pages": [{
    "properties": {
      "タイトル": "Executive Navyカラーシステムの実装",
      "ステータス": "完了",
      "date:期日:start": "2026-01-14",
      "date:期日:is_datetime": 0,
      "見積（h）": 2,
      "責任者": "[\"2b0d872b-594c-8107-b070-0002ce42d546\"]"
    }
  }]
}
```

### 5. 完了報告

登録完了後、作成したタスクの一覧とNotionへのリンクを表示
