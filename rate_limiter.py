"""
リプライレート制限モジュール
1時間あたりのリプライ回数を制限
"""

import logging
from database import Database

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, db: Database, max_per_user_per_hour: int = 3):
        """
        :param db: データベースインスタンス
        :param max_per_user_per_hour: 1ユーザーあたり1時間の最大リプライ数
        """
        self.db = db
        self.max_per_hour = max_per_user_per_hour
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        レート制限チェック
        :param user_id: ユーザーID
        :return: リプライ可能ならTrue
        """
        count = await self.db.get_rate_limit_count(user_id, hours=1)
        
        if count >= self.max_per_hour:
            logger.warning(f"⏱️  レート制限超過: @{user_id} ({count}/{self.max_per_hour})")
            return False
        
        logger.debug(f"✅ レート制限OK: @{user_id} ({count}/{self.max_per_hour})")
        return True
    
    async def record_reply(self, user_id: str):
        """
        リプライを記録
        :param user_id: ユーザーID
        """
        await self.db.record_reply(user_id)
        logger.debug(f"📝 リプライ記録: @{user_id}")
