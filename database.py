"""
データベース管理モジュール
フォロワー管理・投稿履歴・リプライレート制限
"""

import aiosqlite
import logging
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = settings.database_path
        self.db = None
    
    async def connect(self):
        """データベース接続"""
        self.db = await aiosqlite.connect(self.db_path)
        await self._init_tables()
        logger.info("✅ データベース接続成功")
    
    async def close(self):
        """データベース切断"""
        if self.db:
            await self.db.close()
    
    async def _init_tables(self):
        """テーブル初期化"""
        # フォロワーテーブル
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS followers (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                followed_at TEXT NOT NULL,
                is_following_back BOOLEAN DEFAULT 0
            )
        """)
        
        # 投稿履歴テーブル
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT,
                post_type TEXT,
                content TEXT,
                posted_at TEXT NOT NULL
            )
        """)
        
        # リプライレート制限テーブル
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS reply_rate_limits (
                user_id TEXT NOT NULL,
                replied_at TEXT NOT NULL,
                PRIMARY KEY (user_id, replied_at)
            )
        """)
        
        await self.db.commit()
        logger.info("✅ データベーステーブル初期化完了")
    
    # ----- フォロワー管理 -----
    async def get_all_followers(self):
        """全フォロワー取得"""
        async with self.db.execute(
            "SELECT user_id, username, is_following_back FROM followers"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'is_following_back': bool(row[2])
                }
                for row in rows
            ]
    
    async def add_follower(self, user_id: str, username: str):
        """フォロワー追加"""
        try:
            await self.db.execute(
                "INSERT OR IGNORE INTO followers (user_id, username, followed_at) VALUES (?, ?, ?)",
                (user_id, username, datetime.now().isoformat())
            )
            await self.db.commit()
            logger.info(f"📝 フォロワー追加: @{username} ({user_id})")
        except Exception as e:
            logger.error(f"フォロワー追加エラー: {e}")
    
    async def remove_follower(self, user_id: str):
        """フォロワー削除"""
        try:
            await self.db.execute("DELETE FROM followers WHERE user_id = ?", (user_id,))
            await self.db.commit()
            logger.info(f"🗑️  フォロワー削除: {user_id}")
        except Exception as e:
            logger.error(f"フォロワー削除エラー: {e}")
    
    async def set_following_back(self, user_id: str, is_following: bool):
        """フォローバック状態更新"""
        try:
            await self.db.execute(
                "UPDATE followers SET is_following_back = ? WHERE user_id = ?",
                (int(is_following), user_id)
            )
            await self.db.commit()
            logger.debug(f"フォローバック状態更新: {user_id} -> {is_following}")
        except Exception as e:
            logger.error(f"フォローバック状態更新エラー: {e}")
    
    async def is_follower(self, user_id: str) -> bool:
        """フォロワーかチェック"""
        async with self.db.execute(
            "SELECT 1 FROM followers WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None
    
    async def is_following_back(self, user_id: str) -> bool:
        """既にフォローバック済みかチェック"""
        async with self.db.execute(
            "SELECT is_following_back FROM followers WHERE user_id = ?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None and bool(result[0])
    
    # ----- 投稿履歴 -----
    async def add_post(self, note_id: str, post_type: str, content: str):
        """投稿履歴に追加"""
        try:
            await self.db.execute(
                "INSERT INTO posts (note_id, post_type, content, posted_at) VALUES (?, ?, ?, ?)",
                (note_id, post_type, content, datetime.now().isoformat())
            )
            await self.db.commit()
            logger.debug(f"📝 投稿履歴追加: {post_type}")
        except Exception as e:
            logger.error(f"投稿履歴追加エラー: {e}")
    
    # ----- リプライレート制限 -----
    async def get_rate_limit_count(self, user_id: str, hours: int = 1) -> int:
        """
        指定時間内のリプライ数を取得
        :param user_id: ユーザーID
        :param hours: 過去何時間分を集計するか
        :return: リプライ数
        """
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        try:
            async with self.db.execute(
                "SELECT COUNT(*) FROM reply_rate_limits WHERE user_id = ? AND replied_at >= ?",
                (user_id, cutoff_time)
            ) as cursor:
                result = await cursor.fetchone()
                count = result[0] if result else 0
                logger.debug(f"レート制限チェック: @{user_id} = {count}回 (過去{hours}時間)")
                return count
        except Exception as e:
            logger.error(f"レート制限取得エラー: {e}")
            return 0
    
    async def record_reply(self, user_id: str):
        """
        リプライ記録を追加
        :param user_id: ユーザーID
        """
        try:
            await self.db.execute(
                "INSERT INTO reply_rate_limits (user_id, replied_at) VALUES (?, ?)",
                (user_id, datetime.now().isoformat())
            )
            await self.db.commit()
            logger.debug(f"📝 リプライ記録: @{user_id}")
        except Exception as e:
            logger.error(f"リプライ記録エラー: {e}")
    
    async def cleanup_old_rate_limits(self, days: int = 7):
        """
        古いレート制限レコードを削除
        :param days: 何日以前のレコードを削除するか
        """
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            await self.db.execute(
                "DELETE FROM reply_rate_limits WHERE replied_at < ?",
                (cutoff_time,)
            )
            await self.db.commit()
            logger.info(f"🗑️  古いレート制限レコード削除 (>{days}日前)")
        except Exception as e:
            logger.error(f"レート制限クリーンアップエラー: {e}")
