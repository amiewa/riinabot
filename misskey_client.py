import logging
from misskey import Misskey
from config import settings, bot_config

logger = logging.getLogger(__name__)

class MisskeyClient:
    def __init__(self):
        self.client = Misskey(settings.misskey_instance_url, i=settings.misskey_api_token)
        self.default_visibility = bot_config.get("posting.default_visibility", "home")
        logger.info(f"Misskey APIクライアント初期化: {settings.misskey_instance_url}")
        logger.info(f"デフォルト投稿先: {self.default_visibility}")
    
    async def connect(self):
        """Misskey接続確認とユーザー情報取得"""
        try:
            user_info = self.client.i()
            logger.info(f"Misskey接続成功: @{user_info.get('username', 'unknown')}")
            return user_info
        except Exception as e:
            logger.error(f"Misskey接続エラー: {e}")
            raise
    
    async def get_followers(self, limit: int = 100):
        """フォロワー一覧取得"""
        try:
            # Misskey.py 4.1.0 の正しいパラメータ: userId（自分のID）が必要
            user_info = self.client.i()
            user_id = user_info.get("id")
            
            response = self.client.users_followers(userId=user_id, limit=limit)
            
            if isinstance(response, list):
                follower_list = []
                for item in response:
                    if isinstance(item, dict):
                        user = item.get("follower")
                        if user:
                            follower_list.append(user)
                
                logger.debug(f"フォロワー取得: {len(follower_list)}人")
                return follower_list
            else:
                logger.warning(f"予期しないフォロワーレスポンス形式: {type(response)}")
                return []
        except Exception as e:
            logger.error(f"フォロワー取得エラー: {e}")
            return []
    
    async def get_following(self, limit: int = 100):
        """フォロー中一覧取得"""
        try:
            user_info = self.client.i()
            user_id = user_info.get("id")
            
            response = self.client.users_following(userId=user_id, limit=limit)
            
            if isinstance(response, list):
                following_list = []
                for item in response:
                    if isinstance(item, dict):
                        user = item.get("followee")
                        if user:
                            following_list.append(user)
                
                logger.debug(f"フォロー中取得: {len(following_list)}人")
                return following_list
            else:
                logger.warning(f"予期しないフォロー中レスポンス形式: {type(response)}")
                return []
        except Exception as e:
            logger.error(f"フォロー中取得エラー: {e}")
            return []
    
    async def follow_user(self, user_id: str):
        """ユーザーをフォロー"""
        try:
            self.client.following_create(userId=user_id)
            logger.info(f"フォロー成功: {user_id}")
        except Exception as e:
            logger.error(f"フォローエラー ({user_id}): {e}")
            raise
    
    async def unfollow_user(self, user_id: str):
        """ユーザーのフォローを解除"""
        try:
            self.client.following_delete(userId=user_id)
            logger.info(f"フォロー解除成功: {user_id}")
        except Exception as e:
            logger.error(f"フォロー解除エラー ({user_id}): {e}")
            raise
    
    async def send_note(self, text: str, visibility: str = None, reply_id: str = None):
        """ノート投稿"""
        try:
            params = {
                "text": text,
                "visibility": visibility or self.default_visibility
            }
            
            if reply_id:
                params["replyId"] = reply_id
            
            response = self.client.notes_create(**params)
            logger.info(f"ノート投稿成功: {text[:30]}...")
            return response
        except Exception as e:
            logger.error(f"ノート投稿エラー: {e}")
            raise
    
    async def get_mentions(self, limit: int = 10):
        """メンション取得"""
        try:
            response = self.client.i_notifications(
                limit=limit,
                includeTypes=["mention", "reply"]
            )
            
            mentions = []
            if isinstance(response, list):
                for notification in response:
                    if isinstance(notification, dict):
                        notif_type = notification.get("type")
                        if notif_type in ["mention", "reply"]:
                            note = notification.get("note")
                            if note:
                                mentions.append(note)
            
            logger.debug(f"メンション取得: {len(mentions)}件")
            return mentions
        except Exception as e:
            logger.error(f"メンション取得エラー: {e}")
            return []
    
    async def close(self):
        """クライアント終了処理"""
        logger.debug("Misskey クライアント終了")
