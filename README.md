# 担当コードファイル検出（Python）

Excel VBA で作成されていたフォルダ監視マクロを、
**Tkinter ベースの Python アプリ**として再実装したツールです。

指定したフォルダ直下を定期監視し、
**ファイル名先頭の3桁コード**が一致するファイルを検出すると
ポップアップで通知します。

---

## 主な機能

### 監視ロジック（VBA互換）
- 監視対象：**フォルダ直下のファイルのみ**
- 検出条件：
  - ファイル名（拡張子除外）の先頭3文字が数字
  - 4文字目が数字の場合は除外（例：`0012_...` は除外）
  - 3桁コードが監視設定と一致
- Office 一時ファイル（`~$`）は除外
- 保存中チェック：
  - **2秒待機してファイルサイズが変わらない場合のみ有効**（固定値）

### 通知仕様
- 監視サイクルごとに **1回のポップアップに全フォルダ分まとめて表示**
- 長時間放置しても **多重ポップアップは出ない**
- 表示方法：
  - 「閉じるまで常時表示」
  - または「指定秒数で自動クローズ」

### 監視対象管理
- 監視対象は **「担当コード（3桁）＋フォルダ」** のペア
- 同一フォルダ × 複数コード可
- 同一コード × 複数フォルダ可
- 編集・複製・論理削除・完全削除に対応

### スタートアップ登録（Windowsのみ）
- PyInstaller で exe 化された場合のみ有効
- ユーザー単位でスタートアップ登録 / 解除が可能

---

## ディレクトリ構成

```
watcher_app/
  main.py
  app/
    constants.py
    utils.py
    config.py
    monitor.py
    startup.py
    ui.py
    views/
      settings_view.py
      new_item_view.py
      edit_item_view.py
      watch_list_view.py
      purge_view.py
      popup_manager.py
```

---

## 開発環境
- Python 3.13
- macOS / Windows
- パッケージ管理：uv

---

## 環境構築（uv）

### uv のインストール
```bash
curl -Ls https://astral.sh/uv/install.sh | bash
```

### 依存関係の同期
```bash
uv sync
```

---

## 実行方法（開発時）
```bash
uv run main.py
```

---

## macOS でのスタートアップ機能UI確認
```bash
STARTUP_DEBUG=1 uv run main.py
```

---

## アプリ化（PyInstaller）

### PyInstaller の追加
```bash
uv add pyinstaller
```

### ビルド
```bash
uv run pyinstaller --onefile --noconsole --name FileWatcher main.py
```

### 出力
```
dist/
  FileWatcher.exe  (Windows)
  FileWatcher      (macOS)
```

---

## 注意事項
- サブフォルダは監視対象外
- 同一ファイルは次サイクルでも検出されます（VBA互換）
