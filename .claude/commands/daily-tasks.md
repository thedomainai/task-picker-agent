# Task Picker Agent

Cursor内の作業からタスクを拾い上げ、tasks.mdに追加します。
当日更新されたファイルから、追加されたタスクと完了したタスクを検出します。

## 実行手順

### 1. 今日の日付
$CURRENT_DATE

### 2. 情報収集

以下のソースからタスクを抽出してください：

#### 2.1 当日更新されたファイルを検出
ワークスペース内で今日更新された.mdファイルを検出：

```bash
# 今日更新された.mdファイルを検出
find /Users/lemmaitt/workspace/obsidian_vault -name "*.md" -mtime -1 -type f 2>/dev/null | head -50
```

#### 2.2 Git差分からタスクの追加・完了を検出
Git管理下のリポジトリで、タスクの変化を検出：

```bash
# 各リポジトリでタスクの追加・完了を検出
find ~/workspace -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  # 今日のコミットがあるリポジトリのみ処理
  if git -C "$repo" log --oneline --since="today 00:00" 2>/dev/null | grep -q .; then
    echo "=== $repo ==="
    # タスクの追加（+ - [ ]）と完了（- - [ ] → + - [x]）を検出
    git -C "$repo" diff HEAD~3 -- "*.md" 2>/dev/null | grep -E "^[\+\-].*\- \[.\]" | head -20
  fi
done
```

**検出パターン:**
- `+ - [ ] タスク` → 新規追加されたタスク
- `- - [ ] タスク` → 削除または完了に変更されたタスク
- `+ - [x] タスク` → 完了としてマークされたタスク

#### 2.3 Claude Codeセッションログから抽出
今日更新されたセッションログを読み取り、タスクを抽出：

```bash
# 今日のセッションログを確認
find /Users/lemmaitt/workspace/obsidian_vault/docs/01_resource/sessions -name "*.md" -mtime -1 -type f 2>/dev/null
```

各セッションファイル内の `## Tasks` セクションからタスクを抽出。

#### 2.4 更新されたドキュメントからTODO/FIXMEを抽出
今日更新されたファイル内のTODO/FIXMEを検索：

```bash
# 今日更新されたファイルからTODO/FIXMEを抽出
find /Users/lemmaitt/workspace/obsidian_vault -name "*.md" -mtime -1 -type f -exec grep -l "TODO\|FIXME\|\- \[ \]" {} \; 2>/dev/null
```

### 3. タスク一覧の作成

収集した情報から、以下の形式でタスク一覧を作成：

```markdown
## Tasks picked on YYYY-MM-DD

### 🆕 追加されたタスク
- [ ] 新しく追加されたタスク1（ファイル名）
- [ ] 新しく追加されたタスク2（ファイル名）

### ✅ 完了したタスク
- [x] 完了したタスク1（ファイル名）
- [x] 完了したタスク2（ファイル名）

### 📋 セッションログからのタスク
- [ ] セッション内タスク（session-xxxx）

### 📝 ドキュメント内のTODO/FIXME
- [ ] TODO: 説明（ファイル名）
```

### 4. tasks.mdへの追記

ユーザー確認後、以下のファイルに追記：

```
/Users/lemmaitt/workspace/obsidian_vault/docs/01_resource/tasks.md
```

### 5. 完了報告

追加したタスク数と完了したタスク数のサマリーを表示。
