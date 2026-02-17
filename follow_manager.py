"""
フォロー管理モジュール
自動フォローバック・リムーブバック機能
"""

import logging
from misskey_client import MisskeyClient
from database import Database
from config import bot_config

logger = logging.getLogger(__name__)

class FollowManager:
    def __init__(self, misskey: MisskeyClient, db: Database):
        """
        :param misskey: Misskeyクライアント
        :param db: データベース
        """
        self.misskey = misskey
        self.db = db
        self.auto_follow_back = bot_config.get("follow.auto_follow_back", False)
        self.auto_unfollow_back = bot_config.get("follow.auto_unfollow_back", True)
    
    async def check_and_sync_followers(self):
        """
        フォロワーとフォロー状態を同期
        - 新しいフォロワー → データベースに追加
        - フォロー解除されたユーザー → 自動リムーブバック
        """
        logger.info("フォロー状態の同期を開始")
        try:
            current_followers = await self.misskey.get_followers()
            current_follower_ids = {f['id'] for f in current_followers}
            
            db_followers = await self.db.get_all_followers()
            db_follower_ids = {f['user_id'] for f in db_followers}
            
            new_follower_ids = current_follower_ids - db_follower_ids
            unfollowed_ids = db_follower_ids - current_follower_ids
            
            for follower in current_followers:
                if follower['id'] in new_follower_ids:
                    await self.handle_new_follower(follower)
            
            for user_id in unfollowed_ids:
                await self.handle_unfollower(user_id)
            
            logger.info(f"フォロー同期完了: 新規{len(new_follower_ids)}人, 解除{len(unfollowed_ids)}人")
        except Exception as e:
            logger.error(f"フォロー同期エラー: {e}")
    
    async def handle_new_follower(self, follower):
        """
        新しいフォロワーへの対応
        - データベースに追加
        - 自動フォローバックは無効化 (キーワード検出時のみフォローバック)
        """
        user_id = follower['id']
        username = follower['username']
        logger.info(f"新しいフォロワー: @{username} ({user_id})")
        await self.db.add_follower(user_id, username)
        
        # 自動フォローバックは無効化済み
        if self.auto_follow_back:
            logger.warning("自動フォローバックは無効化されています (キーワード検出時のみ)")
    
    async def handle_unfollower(self, user_id: str):
        """
        フォロー解除されたユーザーへの対応
        - 自動リムーブバック (設定で有効な場合)
        - データベースから削除
        """
        logger.info(f"フォロー解除検出: {user_id}")
        
        if self.auto_unfollow_back:
            # フォローバック済みかチェック
            is_following = await self.db.is_following_back(user_id)
            if is_following:
                try:
                    await self.misskey.unfollow_user(user_id)
                    logger.info(f"✅ 自動リムーブバック: {user_id}")
                except Exception as e:
                    logger.error(f"リムーブバック失敗: {user_id} - {e}")
        
        await self.db.remove_follower(user_id)
