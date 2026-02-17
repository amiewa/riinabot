# Misskeyおしゃべりbot 要件定義書

**作成日**: 2026-02-17  
**プロジェクト名**: りいなちゃんbot (仮)  
**対象プラットフォーム**: Misskey  
**開発環境**: Debian 13 + Docker + Python + SQLite

---

## 1. プロジェクト概要

Misskeyインスタンス上で動作する、キャラクター性を持ったおしゃべりbotを開発する。
Gemini API(gemini-2.5-flash, 思考機能あり)を活用し、自然な会話と自律的な投稿を実現する。

---

## 2. 機能要件

### 2.1 フォロー管理機能

#### 2.1.1 自動フォローバック
- **機能**: フォローされたアカウントを自動的にフォローバックする
- **トリガー**: フォロー通知の受信
- **実装優先度**: 高

#### 2.1.2 自動リムーブバック
- **機能**: リムーブ(フォロー解除)されたアカウントを自動的にリムーブバックする
- **トリガー**: フォロー解除の検知(定期チェック)
- **実装優先度**: 高

---

### 2.2 投稿機能

#### 2.2.1 共通仕様
- **夜間投稿停止**: 23:00 - 5:00 は投稿を行わない
  - ※リプライ返信は夜間も動作(後述)
- **キャラクター設定の反映**: 全投稿にbotの性格・口調を反映

---

#### 2.2.2 定時投稿機能

**概要**: 決められた時間に定型文をランダムで投稿

| 投稿時間帯 | 時刻例 | 投稿内容 |
|---------|-------|---------|
| 朝 | 7:00-8:00 | 「おはよう!」系の挨拶文(複数パターン) |
| 昼 | 12:00-13:00 | 「お昼だよ!」系の投稿(複数パターン) |
| 夕方 | 18:00-19:00 | 「お疲れ様!」系の投稿(複数パターン) |

**実装方式**:
- 各時間帯ごとに投稿文のリストを用意
- ランダムに1つ選択して投稿
- 実装優先度: 中

---

#### 2.2.3 ランダム投稿機能

**概要**: Gemini APIを使用してキャラクター性を持った投稿を自動生成

**仕様**:
- **投稿頻度**: 約1時間に1回(調整可能)
- **生成方法**: Gemini API (gemini-2.5-flash + 思考機能)
- **プロンプト**: botの性格・口調を定義したシステムプロンプト
- **夜間停止**: 23:00-5:00は投稿しない
- 実装優先度: 高

---

#### 2.2.4 タイムライン連動投稿機能

**概要**: タイムラインを読み込み、キーワードをピックアップして投稿

**仕様**:
- **対象タイムライン**: home/local/global から選択可能(設定で切替)
- **キーワード抽出**: ランダムに選んだ投稿からキーワードを抽出
- **除外対象**:
  - NGワードリスト(設定ファイルで管理)
  - カスタム絵文字(`:emoji_name:` 形式)
  - URL(http/https)
  - メンションアカウント名
- **投稿生成**: 抽出したキーワードを使ってGemini APIで文章生成
- 実装優先度: 中

**検討事項**:
- タイムライン読み込み頻度(例: 30分に1回など)
- キーワード抽出ロジック(形態素解析 or Gemini API活用)

---

#### 2.2.5 リプライ応答機能

**概要**: リプライを受けた際に自然な会話で返答

**仕様**:
- **応答方法**: Gemini API (gemini-2.5-flash + 思考機能)
- **応答対象**: **相互フォローのみ**に限定
- **レート制限**: 
  - **1ユーザーあたり1時間に3回まで**
  - 連続応答の制限: 同一会話で5往復まで(調整可能)
- **夜間動作**: 23:00-5:00でも応答する(投稿停止対象外)
- 実装優先度: 高

---

## 3. 技術仕様

### 3.1 開発環境

| 項目 | 詳細 |
|-----|------|
| OS | Debian 13 |
| コンテナ | Docker + Docker Compose |
| 言語 | Python 3.11+ |
| データベース | SQLite |
| Misskey API | Misskey.py (または公式WebSocket API) |
| AI API | Google Gemini API (gemini-2.5-flash) |

**開発方針**:
- プログラムの実装は **AIデベロッパーエージェント** に依頼
- Misskey用Pythonライブラリとしては **Misskey.py (MiPAC)** または **aiohttp + 公式API** を使用

---

### 3.2 システム構成

```
┌─────────────────────────────────────┐
│         Docker Container            │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Misskeybot Application     │  │
│  │   (Python)                   │  │
│  │                              │  │
│  │  - Misskey API Client        │  │
│  │  - Gemini API Client         │  │
│  │  - スケジューラ(APScheduler) │  │
│  │  - WebSocket監視             │  │
│  └──────────────────────────────┘  │
│               ↓↑                   │
│  ┌──────────────────────────────┐  │
│  │      SQLite Database         │  │
│  │  - フォロー管理              │  │
│  │  - レート制限管理            │  │
│  │  - 投稿履歴                  │  │
│  │  - NGワードリスト            │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
          ↓↑              ↓↑
   Misskey Server    Gemini API
```

---

### 3.3 データベース設計(案)

#### テーブル構成

**1. followers (フォロワー管理)**
```sql
CREATE TABLE followers (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    followed_at TIMESTAMP,
    is_following_back BOOLEAN,
    last_checked TIMESTAMP
);
```

**2. rate_limits (レート制限管理)**
```sql
CREATE TABLE rate_limits (
    user_id TEXT,
    action_type TEXT,  -- 'reply', 'mention' など
    timestamp TIMESTAMP,
    PRIMARY KEY (user_id, action_type, timestamp)
);
```

**3. post_history (投稿履歴)**
```sql
CREATE TABLE post_history (
    post_id TEXT PRIMARY KEY,
    post_type TEXT,  -- 'random', 'scheduled', 'timeline', 'reply'
    content TEXT,
    created_at TIMESTAMP
);
```

**4. ng_words (NGワード)**
```sql
CREATE TABLE ng_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE,
    added_at TIMESTAMP
);
```

**5. config (設定管理)**
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP
);
```

---

### 3.4 必要なPythonライブラリ(推定)

```txt
misskey.py  # Misskey API クライアント
google-generativeai  # Gemini API
apscheduler  # スケジュール実行
aiosqlite  # 非同期SQLite
pydantic  # 設定管理
python-dotenv  # 環境変数管理
aiohttp  # 非同期HTTP
```

---

## 4. 設定ファイル構成(案)

### 4.1 環境変数 (.env)
```env
MISSKEY_INSTANCE_URL=https://your-instance.example.com
MISSKEY_API_TOKEN=your_misskey_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4.2 bot設定 (config.yaml)
```yaml
bot:
  character:
    name: "りいなちゃん"
    personality: "明るく元気な女の子。フレンドリーで親しみやすい口調"
    prompt: |
      あなたは「りいなちゃん」というキャラクターです。
      明るく元気で、誰とでもすぐに仲良くなれる性格です。
      口調は親しみやすく、絵文字も適度に使います。

posting:
  night_mode:
    enabled: true
    start_hour: 23  # 23:00
    end_hour: 5     # 5:00
  
  random_post:
    enabled: true
    interval_minutes: 60  # 1時間に1回
  
  scheduled_posts:
    - time: "07:30"
      messages:
        - "おはよう!今日もいい天気だね☀️"
        - "おはよー!朝ごはん食べた?"
        - "おっはよー!今日も頑張ろうね!"
    
    - time: "12:00"
      messages:
        - "お昼だよ!お昼ごはん何食べる?"
        - "ランチタイム!今日のお昼は何かな?"
    
    - time: "18:30"
      messages:
        - "お疲れ様!今日も1日頑張ったね!"
        - "夕方だね~お疲れ様でした!"

  timeline_post:
    enabled: true
    source: "home"  # home/local/global
    interval_minutes: 10  # 10分に1回キーワードピックアップ
    ng_words:
      - "死ね"
      - "バカ"
      # NGワードを追加

reply:
  enabled: true
  restriction: "mutual"  # mutual/follower/all
  rate_limit:
    per_user_per_hour: 3
    max_conversation_depth: 5
  ignore_night_mode: true

follow:
  auto_follow_back: true
  auto_unfollow_back: true
  check_interval_minutes: 10
```

---

## 5. 実装ステップ(推奨順序)

### Phase 1: 基盤構築
1. Docker環境のセットアップ
2. Misskey API接続確認
3. Gemini API接続確認
4. SQLiteデータベース構築

### Phase 2: 基本機能
1. フォロー管理機能(自動フォローバック/リムーブバック)
2. ランダム投稿機能
3. 夜間投稿停止機能

### Phase 3: 高度な投稿機能
1. 定時投稿機能
2. リプライ応答機能
3. レート制限機能

### Phase 4: 拡張機能
1. タイムライン連動投稿
2. NGワード管理UI(CLI)
3. ログ・モニタリング機能

---

## 6. セキュリティ・運用考慮事項

### 6.1 セキュリティ
- [ ] API Tokenの安全な管理(.envファイル、Gitignore設定)
- [ ] レート制限による過負荷防止
- [ ] NGワードフィルタによる不適切投稿の防止
- [ ] エラーハンドリングとログ管理

### 6.2 運用
- [ ] Dockerコンテナの自動再起動設定
- [ ] ログローテーション
- [ ] 定期バックアップ(SQLiteデータベース)
- [ ] モニタリング(稼働状態確認)

---

## 7. 未確定事項・要検討項目

1. **vibecordingの用途確認**
   - Misskey用ライブラリとしての使用可否
   - 代替としてMisskey.pyまたは公式API直接利用を検討

2. **タイムライン読み込み頻度**
   - キーワード抽出の実行間隔: **10分に1回**

3. **キーワード抽出方法**
   - 形態素解析(MeCab/Janome)
   - Gemini APIによる抽出
   - シンプルな頻出単語抽出

4. **レート制限の具体的数値**
   - 1ユーザーあたりの応答回数: **1時間に3回まで**
   - 会話の最大深度: 5往復(調整可能)
   - 応答対象: **相互フォローのみ**

5. **キャラクター設定の詳細**
   - 口調・性格の具体的な設定
   - 専門知識や趣味の設定
   - ※別チャットで作成済みのプロンプトをHubにアップロード予定

---

## 8. 参考リソース

- [Misskey API Documentation](https://misskey-hub.net/docs/api/)
- [Misskey.py GitHub](https://github.com/yupix/MiPAC)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

---

## 変更履歴

| 日付 | 変更内容 | 担当 |
|-----|---------|-----|
| 2026-02-17 | 初版作成 | - |

