"""
リプライ管理モジュール
メンション検出・キーワードフォローバック・Gemini返信
"""

import logging
from misskey_client import MisskeyClient
from gemini_client import GeminiClient
from database import Database
from rate_limiter import RateLimiter
from config import bot_config

logger = logging.getLogger(__name__)

class ReplyManager:
    def __init__(self, misskey: MisskeyClient, gemini: GeminiClient, db: Database):
        """
        :param misskey: Misskeyクライアント
        :param gemini: Geminiクライアント
        :param db: データベース
        """
        self.misskey = misskey
        self.gemini = gemini
        self.db = db
        
        # レート制限
        max_per_hour = bot_config.get("reply.rate_limit.max_per_user_per_hour", 3)
        self.rate_limiter = RateLimiter(db, max_per_hour)
        
        # リプライ制限設定
        self.reply_enabled = bot_config.get("reply.enabled", True)
        self.mutual_only = bot_config.get("reply.mutual_only", True)
        
        # キーワードフォローバック
        self.keyword_follow_enabled = bot_config.get("follow.keyword_follow_back.enabled", True)
        self.follow_keywords = bot_config.get("follow.keyword_follow_back.keywords", [])
        
        # 最後に確認したメンションID
        self.last_mention_id = None
    
    async def check_mentions(self):
        """メンション確認 (1分ごと)"""
        if not self.reply_enabled:
            return
        
        try:
            # 未読メンション取得
            mentions = await self.misskey.get_mentions(limit=10)
            
            for mention in mentions:
                mention_id = mention.get('id')
                
                # 既読スキップ
                if self.last_mention_id and mention_id == self.last_mention_id:
                    break
                
                await self.handle_mention(mention)
            
            # 最新メンションIDを記録
            if mentions:
                self.last_mention_id = mentions[0].get('id')
                
        except Exception as e:
            logger.error(f"メンション確認エラー: {e}")
    
    async def handle_mention(self, mention: dict):
        """
        メンション処理
        - キーワードフォローバック検出
        - リプライ生成
        """
        user = mention.get('user', {})
        user_id = user.get('id')
        username = user.get('username')
        text = mention.get('text', '')
        
        logger.info(f"📩 メンション受信: @{username} - {text[:50]}...")
        
        # キーワードフォローバック検出
        is_follow_keyword = self.keyword_follow_enabled and any(kw in text for kw in self.follow_keywords)
        
        if is_follow_keyword:
            await self.handle_keyword_follow(user_id, username)
            # キーワードフォローバックの場合はリプライをスキップ
            logger.info(f"⏸️  キーワードフォローバック完了: リプライスキップ (@{username})")
            return
        
        # 通常のリプライ処理
        await self.handle_reply(mention)
    
    async def handle_keyword_follow(self, user_id: str, username: str):
        """
        キーワードフォローバック処理
        """
        try:
            # 既にフォロワーかチェック
            is_follower = await self.db.is_follower(user_id)
            if not is_follower:
                logger.info(f"⏸️  フォロワーでないユーザー: @{username}")
                return
            
            # 既にフォローバック済みかチェック
            already_following = await self.db.is_following_back(user_id)
            if already_following:
                logger.info(f"既にフォローバック済み: @{username}")
                return
            
            # フォローバック実行
            await self.misskey.follow_user(user_id)
            await self.db.set_following_back(user_id, True)
            logger.info(f"✅ キーワードフォローバック: @{username}")
            
        except Exception as e:
            logger.error(f"キーワードフォローバックエラー (@{username}): {e}")
    
    async def handle_reply(self, mention: dict):
        """
        リプライ処理
        - 権限チェック (mutual_only)
        - レート制限チェック
        - Gemini返信生成
        """
        user = mention.get('user', {})
        user_id = user.get('id')
        username = user.get('username')
        text = mention.get('text', '')
        mention_id = mention.get('id')
        
        try:
            # 権限チェック
            if not await self._check_reply_permission(user_id):
                logger.info(f"⏸️  リプライスキップ (権限不足): @{username}")
                return
            
            # レート制限チェック
            if not await self.rate_limiter.check_rate_limit(user_id):
                logger.info(f"⏸️  リプライスキップ (レート制限): @{username}")
                return
            
            # Gemini返信生成
            reply_text = await self.gemini.generate_reply(text, username)
            
            if reply_text is None:
                logger.warning(f"⏸️  Gemini APIエラー: リプライスキップ (@{username})")
                return
            
            # Misskeyにリプライ投稿
            await self.misskey.reply_to_note(mention_id, reply_text)
            
            # レート制限記録
            await self.rate_limiter.record_reply(user_id)
            
            # データベースに記録
            await self.db.add_post(mention_id, "reply", reply_text)
            
            logger.info(f"✅ リプライ完了: @{username}")
            
        except Exception as e:
            logger.error(f"リプライエラー (@{username}): {e}")
    
    async def _check_reply_permission(self, user_id: str) -> bool:
        """
        リプライ権限チェック
        - mutual_only: 相互フォローのみ
        """
        if not self.mutual_only:
            return True
        
        # フォロワーかつフォローバック済みか
        is_follower = await self.db.is_follower(user_id)
        is_following_back = await self.db.is_following_back(user_id)
        
        return is_follower and is_following_back
