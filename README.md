# Misskeybot「りいなちゃん」Phase 3.2

Misskeyで動作する、キャラクター性を持ったおしゃべりbot「りいなちゃん」の実装です。

## 🎉 Phase 3.2 最新機能

**Phase 3.2 で追加された機能**:
- ✅ **タイムライン連動投稿** 🆕🔥
  - home/local/global タイムラインからキーワード抽出
  - キーワードに基づいた自然な独り言投稿
  - 記号・数字のみの単語を自動除外
- ✅ **外部NGワードリスト対応** 🆕
  - config.yaml で複数のNGワードリストURLを指定可能
  - 起動時に自動取得・統合
  - OSSのNGワードリスト（goodBadWordlist）対応
- ✅ **キャラクター設定の完全反映**
  - Gemini API の system_instruction 対応
  - キャラクターらしい口調・性格が正確に反映
  - リプライ長の最適化（50〜120文字程度）

**Phase 3 からの継続機能**:
- ✅ **WebSocketストリーミング**
  - リアルタイムフォロー通知 → 即座にフォローバック
  - リアルタイムリプライ/メンション通知 → 即座に返答
- ✅ **リプライ応答機能**
  - 相互フォローのみ応答
  - レート制限: 1ユーザー/1時間に3回まで
  - 夜間も応答可能
- ✅ **定時投稿機能**
  - 朝・昼・午後・夕方・夜 の5回定時投稿
  - 各時間帯で複数パターンからランダム選択
- ✅ **データベース・ログメンテナンス**
  - 古いレコード自動削除
  - 自動バックアップ（圧縮対応）
  - ログローテーション

**Phase 1 からの継続機能**:
- ✅ Docker環境 + Python + SQLite 基盤
- ✅ Misskey API連携 (Misskey.py 4.1.0)
- ✅ Gemini API連携 (gemini-2.5-flash)
- ✅ キーワードフォローバック機能
- ✅ 自動リムーブバック
- ✅ ランダム投稿 (1時間に1回)
- ✅ 夜間投稿停止 (リプライは夜間も動作)

---

## 📋 前提条件

- Docker & Docker Compose
- MisskeyインスタンスのアカウントとAPIトークン
- Google Gemini API Key

---

## 🚀 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/amiewa/riinabot.git
cd riinabot
```

### 2. 環境変数設定

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

`.env` を編集して、以下の情報を入力:

```env
# Misskey設定
MISSKEY_INSTANCE_URL=https://your-instance.example.com
MISSKEY_API_TOKEN=your_misskey_api_token_here

# Gemini API設定
GEMINI_API_KEY=your_gemini_api_key_here

# その他はデフォルトでOK
TIMEZONE=Asia/Tokyo
DATABASE_PATH=data/riina_bot.db
LOG_LEVEL=INFO
```

#### Misskey APIトークンの取得方法

1. Misskeyインスタンスにログイン
2. 設定 → API → アクセストークンの発行
3. 以下の権限を有効化:
   - ✅ ノートを作成・削除する
   - ✅ フォロー・フォロー解除する
   - ✅ アカウント情報を見る
   - ✅ フォロー・フォロワー情報を見る
   - ✅ 通知を見る
   - ✅ ストリームに接続する
4. 発行されたトークンを `.env` に記入

### 3. 設定ファイルの確認・編集

`config.yaml` を必要に応じて編集:

```yaml
posting:
  # ランダム投稿
  random_post:
    enabled: true
    interval_minutes: 60
  
  # 定時投稿
  scheduled_posts:
    enabled: true
    posts:
      "07:30": ["おはよう～", "朝だよ～"]
      # ... (複数の時間帯)
  
  # ★ タイムライン連動投稿 (Phase 3.2)
  timeline_post:
    enabled: true
    source: "global"  # home/local/global
    interval_minutes: 30  # 実行間隔
    max_notes_fetch: 20
    min_keyword_length: 2
    
    # 基本NGワード
    ng_words:
      - "死ね"
      - "バカ"
    
    # 外部NGワードリスト（URL指定）
    ng_word_urls:
      - "https://raw.githubusercontent.com/sayonari/goodBadWordlist/main/ja/BadList.txt"

follow:
  auto_follow_back: false  # キーワードフォローのみ
  auto_unfollow_back: true
  
  keyword_follow_back:
    enabled: true
    keywords:
      - "フォローして"
      - "相互フォロー"

reply:
  enabled: true
  mutual_only: true
  rate_limit:
    max_per_user_per_hour: 3
```

### 4. Docker起動

```bash
docker compose up -d
```

### 5. 動作確認

ログを確認:

```bash
docker compose logs -f
```

正常に起動すると、以下のようなログが表示されます:

```
riina_bot | 📋 config.yaml から NGワード読み込み: 4件
riina_bot | 🌐 外部NGワードリスト取得中: https://raw.githubusercontent.com/...
riina_bot | ✅ 外部NGワード追加: 152件 (合計: 156件)
riina_bot | 📊 NGワード総数: 156件
riina_bot | === りいなちゃんbot 起動 (Phase 3.2: NGWord Manager) ===
riina_bot | ✅ ランダム投稿: 60分ごと
riina_bot | ✅ タイムライン連動投稿: 30分ごと (対象: global)
riina_bot | ✅ フォロー状態チェック: 30分ごと (定期同期)
riina_bot | ✅ WebSocket接続成功
riina_bot | === Bot起動完了 ===
```

---

## 🎯 Phase 3.2 新機能の使い方

### 1. タイムライン連動投稿

**動作の流れ**:
1. 設定間隔ごと（デフォルト30分）にタイムラインを取得
2. キーワードを抽出（URL、メンション、絵文字、記号を除外）
3. NGワードでフィルタリング
4. ランダムにキーワードを選択
5. Gemini API でキャラクターらしい独り言を生成
6. 投稿

**ログ例**:
```
riina_bot | ✅ タイムライン取得成功: 20件 (global)
riina_bot | 🔍 キーワード抽出: 45個
riina_bot | 📝 選択されたキーワード: ラーメン
riina_bot | ✅ タイムライン連動投稿生成成功 (65文字): タイムラインでラーメンって見かけた〜 食べたくなっちゃった♪
riina_bot | ✅ タイムライン連動投稿完了
```

**除外されるキーワード例**:
- `.day` → 記号で始まる
- `#hashtag` → 記号で始まる
- `@username` → メンション
- `123` → 数字のみ
- `https://...` → URL

### 2. 外部NGワードリスト

**メリット**:
- OSSのNGワードリストを活用できる
- config.yaml に全て書く必要がない
- 複数のリストを統合可能

**設定例**:
```yaml
posting:
  timeline_post:
    ng_word_urls:
      - "https://raw.githubusercontent.com/sayonari/goodBadWordlist/main/ja/BadList.txt"
      - "https://example.com/your-custom-ngword-list.txt"  # 複数指定可能
```

### 3. キャラクター設定の完全反映

**改善点**:
- Gemini API の `system_instruction` に正しく設定
- `max_output_tokens=1024` で十分な長さを確保
- キャラクターの口調・性格が正確に反映

**リプライ例**:
```
ユーザー: @katariina フィンランドと日本、どっちが好き？
りいな: ん〜、どっちも大好きだから困っちゃう質問だね〜！ 
       甲府盆地の夏は暑いけど、富士山も見えるし温泉もあるし最高だよ♪ 
       でもフィンランドのサウナと白夜も恋しくなるんだよね〜
```

---

## 🛠️ 操作方法

### Bot停止

```bash
docker compose down
```

### Bot再起動

```bash
docker compose restart
```

### ログ確認

```bash
# リアルタイムログ
docker compose logs -f

# 特定のキーワードでフィルタ
docker compose logs -f | grep -E "(タイムライン|キーワード|NGワード)"

# 最新100行
docker compose logs --tail=100
```

### データベース確認

```bash
# コンテナ内に入る
docker compose exec riina_bot sh

# SQLiteでデータベースを開く
sqlite3 data/riina_bot.db

# フォロワー一覧
SELECT * FROM followers;

# 投稿履歴（タイムライン連動投稿）
SELECT * FROM post_history WHERE post_type='timeline' ORDER BY created_at DESC LIMIT 10;

# 終了
.exit
```

---

## 📁 ファイル構成 (Phase 3.2)

```
riinabot/
├── main.py                       # メインプログラム
├── config.py                     # 設定管理
├── database.py                   # データベース管理
├── misskey_client.py             # Misskey API (Misskey.py 4.1.0)
├── gemini_client.py              # Gemini API (system_instruction対応)
├── follow_manager.py             # フォロー管理
├── post_manager.py               # ランダム投稿管理
├── scheduled_post_manager.py     # 定時投稿管理
├── streaming_manager.py          # WebSocketストリーミング
├── reply_manager.py              # リプライ管理
├── timeline_post_manager.py      # 🆕 タイムライン連動投稿
├── ng_word_manager.py            # 🆕 NGワード管理
├── database_maintenance.py       # データベースメンテナンス
├── log_maintenance.py            # ログメンテナンス
├── requirements.txt              # Python依存関係
├── Dockerfile                    # Dockerイメージ定義
├── docker-compose.yml            # Docker Compose設定
├── .env.example                  # 環境変数サンプル
├── config.yaml                   # 設定ファイル
├── katariina_prompt.md           # キャラクタープロンプト
├── rdd.md                        # 要件定義書
├── .gitignore                    # Git除外設定
└── README.md                     # このファイル
```

---

## 🐛 トラブルシューティング

### タイムライン連動投稿が動作しない

1. **設定確認**
   ```yaml
   posting:
     timeline_post:
       enabled: true  # ← これが true になっているか
   ```

2. **ログ確認**
   ```bash
   docker compose logs | grep "タイムライン"
   ```

3. **キーワードが抽出できない場合**
   - `min_keyword_length` を 1 に下げる
   - NGワードが多すぎないか確認

### 外部NGワードリストが取得できない

1. **URLの確認**
   - ブラウザで直接アクセスできるか確認

2. **ネットワーク確認**
   - コンテナからインターネットにアクセスできるか

3. **ログ確認**
   ```bash
   docker compose logs | grep "外部NGワード"
   ```

### リプライが短すぎる / 長すぎる

1. **`gemini_client.py` の `max_output_tokens` を調整**
   - デフォルト: 1024
   - 短い場合: 2048 に増やす
   - 長い場合: 512 に減らす

2. **プロンプトで文字数指示を明確化**
   ```python
   prompt = f"""
   - 50〜120文字程度  # ← この指示を調整
   ```

### データベース保存エラー

エラー: `Error binding parameter 1: type 'dict' is not supported`

**原因**: `note_id` が辞書型で返されている

**修正**: `timeline_post_manager.py` で既に対応済み
```python
note_id_str = str(note_id) if not isinstance(note_id, str) else note_id
```

---

## 📊 各機能の実行間隔

| 機能 | デフォルト間隔 | 設定項目 |
|------|--------------|---------|
| ランダム投稿 | 60分 | `posting.random_post.interval_minutes` |
| タイムライン連動投稿 | 30分 | `posting.timeline_post.interval_minutes` |
| フォロー状態チェック | 30分 | `follow.check_interval_minutes` |
| 定時投稿 | 固定時刻 | `posting.scheduled_posts.posts` |
| データベースクリーンアップ | 毎日 03:00 | `maintenance.cleanup_time` |
| データベースバックアップ | 毎日 04:00 | `maintenance.backup_time` |
| ログローテーション | 毎日 05:00 | `maintenance.log_rotate_time` |

---

## 🔄 アップグレード方法

### Phase 3 → Phase 3.2

1. **最新コードを取得**
   ```bash
   cd ~/riina/phase3
   git pull origin main
   ```

2. **config.yaml に追加**
   ```yaml
   posting:
     timeline_post:
       enabled: true
       source: "global"
       interval_minutes: 30
       ng_word_urls:
         - "https://raw.githubusercontent.com/sayonari/goodBadWordlist/main/ja/BadList.txt"
   ```

3. **再ビルド & 起動**
   ```bash
   docker compose down
   docker compose build
   docker compose up -d
   ```

---

## 🎨 カスタマイズ例

### 1. タイムライン連動投稿の頻度を変える

```yaml
posting:
  timeline_post:
    interval_minutes: 10  # 10分に1回（頻繁）
    # または
    interval_minutes: 60  # 1時間に1回（控えめ）
```

### 2. 対象タイムラインを変更

```yaml
posting:
  timeline_post:
    source: "home"   # ホームタイムライン（フォロー中のみ）
    # または
    source: "local"  # ローカルタイムライン（インスタンス内）
    # または
    source: "global" # グローバルタイムライン（全連合）
```

### 3. 独自のNGワードリストを追加

```yaml
posting:
  timeline_post:
    ng_words:
      - "カスタムNGワード1"
      - "カスタムNGワード2"
    ng_word_urls:
      - "https://your-domain.com/your-ngword-list.txt"
```

---

## 📄 ライセンス

このプロジェクトは個人利用目的で作成されています。

---

## 🙏 謝辞

- [Misskey.py](https://github.com/yupix/MiPAC) - Misskey API クライアント
- [goodBadWordlist](https://github.com/sayonari/goodBadWordlist) - NGワードリスト
- [Google Gemini](https://ai.google.dev/) - AI API

---

**りいなちゃんとリアルタイムでおしゃべりしよう!** 🎉💬
