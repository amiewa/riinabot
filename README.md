# Misskeybot「りいなちゃん」Phase 3

Misskeyで動作する、キャラクター性を持ったおしゃべりbot「りいなちゃん」の実装です。

## 🎉 Phase 3 新機能

**Phase 1の機能に加えて**:
- ✅ **WebSocketストリーミング** 🔥
  - リアルタイムフォロー通知 → 即座にフォローバック!
  - リアルタイムリプライ/メンション通知 → 即座に返答!
- ✅ **リプライ応答機能**
  - 相互フォローのみ応答
  - レート制限: 1ユーザー/1時間に3回まで
  - 夜間も応答可能
- ✅ **定時投稿機能**
  - 朝 (7:30)・昼 (12:00)・夕 (18:30) に定型文投稿
  - 各時間帯で複数パターンからランダム選択

**Phase 1からの継続機能**:
- ✅ Docker環境 + Python + SQLite 基盤
- ✅ Misskey API連携 (MiPAC使用)
- ✅ Gemini API連携 (思考機能あり)
- ✅ 自動フォローバック・リムーブバック (WebSocket + 定期チェック併用)
- ✅ ランダム投稿 (1時間に1回)
- ✅ 夜間投稿停止 (23:00-5:00、ただしリプライは夜間も動作)

---

## 📋 前提条件

- Docker & Docker Compose
- MisskeyインスタンスのアカウントとAPIトークン
- Google Gemini API Key

---

## 🚀 セットアップ手順

### 1. ファイル準備

```bash
# リポジトリをクローンまたはダウンロード
cd phase2/
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
   - ✅ **通知を見る** (Phase 2で追加)
   - ✅ **ストリームに接続する** (Phase 2で追加)
4. 発行されたトークンを `.env` に記入

### 3. 設定ファイル作成

`config.yaml.example` をコピーして `config.yaml` を作成:

```bash
cp config.yaml.example config.yaml
```

必要に応じて `config.yaml` を編集:

```yaml
bot:
  character_prompt_file: "katariina_prompt.md"
  
posting:
  night_mode:
    enabled: true
    start_hour: 23
    end_hour: 5
  
  random_post:
    enabled: true
    interval_minutes: 60
  
  # 定時投稿設定 (Phase 2)
  scheduled_posts:
    - time: "07:30"
      messages:
        - "おはよう～♪ 今日もいい天気かな？"
        - "おはよー！ 朝ごはん食べた？"
    - time: "12:00"
      messages:
        - "お昼だよ！ お昼ごはん何食べる？"
    - time: "18:30"
      messages:
        - "お疲れ様！ 今日も1日頑張ったね♪"

follow:
  auto_follow_back: true
  auto_unfollow_back: true
  check_interval_minutes: 3  # WebSocket補完用

# リプライ設定 (Phase 2)
reply:
  enabled: true
  restriction: "mutual"  # mutual/follower/all
  rate_limit:
    per_user_per_hour: 3
  ignore_night_mode: true
```

### 4. Docker起動

```bash
docker-compose up -d
```

### 5. 動作確認

ログを確認:

```bash
docker-compose logs -f
```

正常に起動すると、以下のようなログが表示されます:

```
riina_bot | === りいなちゃんbot 起動 (Phase 2) ===
riina_bot | データベース初期化完了
riina_bot | Misskey接続成功: @your_bot_name
riina_bot | WebSocketコールバック設定完了
riina_bot | ランダム投稿: 60分ごと
riina_bot | 定時投稿: 07:30
riina_bot | 定時投稿: 12:00
riina_bot | 定時投稿: 18:30
riina_bot | === Bot起動完了 ===
riina_bot | ✅ WebSocketストリーミング: リアルタイムフォロー・リプライ対応
riina_bot | mainストリームに接続しました
```

---

## 🎯 Phase 2 新機能の使い方

### 1. リアルタイムフォローバック

**Phase 1との違い**:
- Phase 1: 3分ごとにポーリングでチェック → 最大3分の遅延
- **Phase 2**: WebSocketで即座に通知受信 → **0.5秒以内にフォローバック!** 🔥

誰かがあなたのbotをフォローすると:
```
riina_bot | 🔥 リアルタイムフォロー通知: @username
riina_bot | 新しいフォロワー: @username
riina_bot | 自動フォローバック: @username
```

### 2. リプライ自動応答

**動作条件**:
- ✅ 相互フォローのユーザーからのリプライ/メンション
- ✅ レート制限内 (1ユーザー/1時間に3回まで)

誰かがbotにリプライすると:
```
riina_bot | 💬 リアルタイムリプライ通知: @username
riina_bot | リプライ処理開始: @username
riina_bot | リプライ生成: ん〜、それは面白そうだね♪
riina_bot | リプライ完了: @username
```

**レート制限に引っかかった場合**:
```
riina_bot | レート制限超過: @username
```

**相互フォローではない場合**:
```
riina_bot | 応答対象外: @username (相互フォローではない)
```

### 3. 定時投稿

設定した時間になると自動的に投稿:
```
riina_bot | 定時投稿完了 (07:30): おはよう～♪ 今日もいい天気かな？
```

---

## 🛠️ 操作方法

### Bot停止

```bash
docker-compose down
```

### Bot再起動

```bash
docker-compose restart
```

### ログ確認

```bash
# リアルタイムログ
docker-compose logs -f

# 最新100行
docker-compose logs --tail=100
```

### データベース確認

```bash
# コンテナ内に入る
docker-compose exec misskeybot sh

# SQLiteでデータベースを開く
sqlite3 data/riina_bot.db

# フォロワー一覧
SELECT * FROM followers;

# 投稿履歴
SELECT * FROM post_history ORDER BY created_at DESC LIMIT 10;

# レート制限状況
SELECT user_id, COUNT(*) as count 
FROM rate_limits 
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY user_id;

# 終了
.exit
```

---

## 📁 ファイル構成 (Phase 2)

```
phase2/
├── main.py                       # メインプログラム (WebSocket統合)
├── config.py                     # 設定管理
├── database.py                   # データベース管理 (レート制限機能追加)
├── misskey_client.py             # Misskey API (リプライ機能追加)
├── gemini_client.py              # Gemini API (リプライ生成追加)
├── follow_manager.py             # フォロー管理
├── post_manager.py               # ランダム投稿管理
├── streaming.py                  # 🆕 WebSocketストリーミング
├── reply_manager.py              # 🆕 リプライ管理
├── rate_limiter.py               # 🆕 レート制限管理
├── scheduled_post_manager.py     # 🆕 定時投稿管理
├── requirements.txt              # Python依存関係
├── Dockerfile                    # Dockerイメージ定義
├── docker-compose.yml            # Docker Compose設定
├── .env.example                  # 環境変数サンプル
├── config.yaml.example           # 設定ファイルサンプル (定時投稿・リプライ設定追加)
├── katariina_prompt.md           # キャラクタープロンプト
├── rdd.md                   # 要件定義書
├── .gitignore                    # Git除外設定
└── README.md                     # このファイル
```

---

## 🐛 トラブルシューティング

### WebSocketが接続できない

1. **APIトークンの権限チェック**
   - 「通知を見る」
   - 「ストリームに接続する」
   の権限が必要

2. **ログ確認**
   ```bash
   docker-compose logs | grep WebSocket
   ```

3. **再接続機能**
   - エラーが発生しても5秒後に自動再接続

### リプライが返ってこない

1. **相互フォローチェック**
   - 相互フォローしているか確認
   - `config.yaml` の `reply.restriction` を `"all"` に変更してテスト

2. **レート制限確認**
   - 1時間に3回まで
   - データベースで確認:
     ```sql
     SELECT * FROM rate_limits WHERE user_id='your_user_id';
     ```

3. **夜間設定**
   - リプライは夜間も動作します (`ignore_night_mode: true`)

### 定時投稿が動作しない

1. **タイムゾーン確認**
   - `.env` の `TIMEZONE=Asia/Tokyo` を確認
   - コンテナのタイムゾーンは `docker-compose.yml` で設定済み

2. **設定確認**
   ```bash
   docker-compose logs | grep "定時投稿"
   ```

---

## 🔄 Phase 1からのアップグレード

Phase 1から Phase 2 にアップグレードする場合:

1. **Phase 2 のファイルに置き換え**
2. **`.env` はそのまま使用可能**
3. **`config.yaml` を更新** (定時投稿・リプライ設定を追加)
4. **APIトークンの権限を追加** (通知・ストリーム)
5. **再起動**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

データベースはそのまま引き継がれます。

---

## 📊 次のPhase予定

**Phase 3**: タイムライン連動投稿
- タイムラインからキーワードをピックアップ (10分に1回)
- NGワードフィルタ
- キーワードを使った投稿生成
- カスタム絵文字・URL除外

---

## 📄 ライセンス

このプロジェクトは個人利用目的で作成されています。

---

**りいなちゃんとリアルタイムでおしゃべりしよう!** 🎉💬
