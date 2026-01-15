# Task Picker Agent

Cursor内の作業からタスクを拾い上げ、tasks.mdに追加します。

## 実行手順

### 1. 今日の日付
$CURRENT_DATE

### 2. 情報収集

以下のソースからタスクを抽出してください：

#### 2.1 Claude Codeセッションログから抽出
セッションログを読み取り、`## Tasks` セクションのタスクを抽出：

```bash
# 今月のセッションログを確認
ls /Users/lemmaitt/workspace/obsidian_vault/docs/01_resource/sessions/$(date +%Y-%m)/
```

各セッションファイル内の `## Tasks` セクションから未完了タスク `- [ ]` を抽出。

#### 2.2 Git差分から作業内容を抽出
現在のプロジェクトで変更されたファイルを確認：

```bash
git status --short
git diff --stat HEAD~5  # 直近5コミットの変更
```

変更内容から「何をしたか」「何が残っているか」を推測。

#### 2.3 プロジェクト内ドキュメントから抽出
プロジェクト内の.mdファイルからTODO/FIXMEなどを検索：

```bash
grep -r "TODO\|FIXME\|\- \[ \]" --include="*.md" . 2>/dev/null | head -20
```

### 3. タスク一覧の作成

収集した情報から、以下の形式でタスク一覧を作成：

```markdown
## Tasks picked on YYYY-MM-DD

### From Session Logs
- [ ] タスク1（session-xxxx）
- [ ] タスク2（session-yyyy）

### From Git Changes
- [ ] 変更内容に基づくタスク

### From Documents
- [ ] ドキュメントから抽出したタスク
```

### 4. tasks.mdへの追記

ユーザー確認後、以下のファイルに追記：

```
/Users/lemmaitt/workspace/obsidian_vault/docs/01_resource/tasks.md
```

`## Next Steps` セクションの下に、抽出したタスクを追加。

### 5. 完了報告

追加したタスク数と内容のサマリーを表示。
