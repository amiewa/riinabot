import logging
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class ReplyManager:
    def __init__(self, misskey, gemini, db):
        self.misskey = misskey
        self.gemini = gemini
        self.db = db
        self.rate_limiter = RateLimiter(db, max_per_user_per_hour=3)
        # 処理済みメンションを記録（重複防止）
        self.processed_mentions = set()
    
    async def handle_mention(self, mention: dict):
        """メンション処理: キーワードフォロー or リプライ"""
        mention_id = mention.get("id")
        
        # 重複防止
        if mention_id in self.processed_mentions:
            logger.debug(f"⏭️  処理済みメンションをスキップ: {mention_id}")
            return
        
        # ユーザー情報取得（辞書スタイル）
        user = mention.get("user", {})
        user_id = user.get("id")
        username = user.get("username", "unknown")
        text = mention.get("text", "")
        
        logger.info(f"📩 メンション受信: @{username} - {text[:30]}...")
        logger.debug(f"🔍 DEBUG - User ID: {user_id}, Username: {username}")
        
        # キーワードフォローチェック
        follow_keywords = [
            "フォロー", "ふぉろー", "follow", "フォローバック",
            "フォロバ", "フォローして", "ふぉろーして"
        ]
        
        is_follow_keyword = any(kw in text for kw in follow_keywords)
        
        if is_follow_keyword:
            await self.handle_keyword_follow(user_id, username)
            logger.info(f"⏸️  キーワードフォローバック完了: リプライスキップ (@{username})")
            self.processed_mentions.add(mention_id)
            return
        
        # 通常のリプライ処理
        await self.handle_reply(mention)
        self.processed_mentions.add(mention_id)
    
    async def handle_keyword_follow(self, user_id: str, username: str):
        """キーワードによる自動フォローバック"""
        logger.info(f"🔍 キーワードフォロー判定: @{username}")
        
        # データベースでフォロワー確認
        async with self.db.db.execute(
            "SELECT is_following_back FROM followers WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if row and row[0]:
            logger.info(f"✅ 既にフォローバック済み: @{username}")
            return
        
        # フォローバック実行
        try:
            await self.misskey.follow_user(user_id)
            
            # データベース更新
            await self.db.db.execute("""
                INSERT OR REPLACE INTO followers (user_id, username, is_follower, is_following_back)
                VALUES (?, ?, 1, 1)
            """, (user_id, username))
            await self.db.db.commit()
            
            logger.info(f"✅ キーワードフォローバック成功: @{username}")
        except Exception as e:
            logger.error(f"❌ キーワードフォローバックエラー: {e}")
    
    async def handle_reply(self, mention: dict):
        """リプライ処理"""
        user = mention.get("user", {})
        user_id = user.get("id")
        username = user.get("username", "unknown")
        text = mention.get("text", "")
        mention_id = mention.get("id")
        
        logger.info(f"📝 リプライ処理開始: @{username}")
        logger.debug(f"🔍 DEBUG - mention dict keys: {mention.keys()}")
        logger.debug(f"🔍 DEBUG - user dict keys: {user.keys()}")
        logger.debug(f"🔍 DEBUG - User ID: {user_id}, Username: {username}")
        
        # 1. データベースから相互フォロー状態確認
        async with self.db.db.execute(
            "SELECT is_follower, is_following_back FROM followers WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        logger.debug(f"🔍 DEBUG - DB query result: {row}")
        
        if not row:
            logger.warning(f"⏸️  リプライスキップ (DB未登録): @{username}")
            logger.debug(f"🔍 DEBUG - User {user_id} not found in followers table")
            return
        
        is_follower, is_following_back = row
        logger.debug(f"🔍 DEBUG - is_follower: {is_follower}, is_following_back: {is_following_back}")
        
        # 2. 相互フォローチェック
        if not (is_follower and is_following_back):
            if not is_follower:
                logger.info(f"⏸️  リプライスキップ (フォロワーでないユーザー): @{username}")
            else:
                logger.info(f"⏸️  リプライスキップ (権限不足): @{username}")
            return
        
        logger.info(f"✅ 相互フォロー確認済み: @{username}")
        
        # 3. レート制限チェック
        if not await self.rate_limiter.check_rate_limit(user_id):
            logger.info(f"⏸️  リプライスキップ (レート制限): @{username}")
            return
        
        # 4. リプライ生成
        try:
            reply_text = await self.gemini.generate_reply(username, text)
            logger.debug(f"🔍 DEBUG - Generated reply: {reply_text[:50]}...")
            
            # 5. リプライ送信
            await self.misskey.send_note(
                text=reply_text,
                reply_id=mention_id
            )
            
            # 6. レート制限記録
            await self.rate_limiter.record_reply(user_id)
            
            logger.info(f"✅ リプライ完了: @{username}")
        except Exception as e:
            logger.error(f"❌ リプライ送信エラー: @{username} - {e}")
            logger.debug(f"🔍 DEBUG - Error type: {type(e).__name__}")
            logger.debug(f"🔍 DEBUG - Error details: {str(e)}")
