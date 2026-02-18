"""
定時投稿管理モジュール
設定された時刻に自動投稿
"""

import logging
import random
from misskey_client import MisskeyClient
from gemini_client import GeminiClient
from database import Database
from config import bot_config

logger = logging.getLogger(__name__)

class ScheduledPostManager:
    def __init__(self, misskey: MisskeyClient, gemini: GeminiClient, db: Database):
        """
        :param misskey: Misskeyクライアント
        :param gemini: Geminiクライアント
        :param db: データベース
        """
        self.misskey = misskey
        self.gemini = gemini
        self.db = db
    
    async def post_scheduled(self, time_key: str):
        """
        指定時刻の定時投稿を実行
        :param time_key: 時刻キー (例: "07:30")
        """
        logger.info(f"⏰ 定時投稿実行: {time_key}")
        
        try:
            # config.yamlから該当時刻のメッセージリストを取得
            scheduled_posts = bot_config.get("posting.scheduled_posts.posts", {})
            messages = scheduled_posts.get(time_key, [])
            
            if not messages:
                logger.warning(f"定時投稿メッセージが未設定: {time_key}")
                return
            
            # ランダムに1つ選択
            content = random.choice(messages)
            
            # Misskeyに投稿
            response = await self.misskey.send_note(content)
            
            # レスポンスからノートIDを取得
            if isinstance(response, dict):
                note_id = response.get('createdNote', {}).get('id', 'unknown')
            else:
                note_id = str(response) if response else 'unknown'
            
            # データベースに記録
            await self.db.add_post(note_id, f"scheduled_{time_key}", content)
            
            logger.info(f"✅ 定時投稿成功 ({time_key}): {content[:50]}...")
            
        except Exception as e:
            logger.error(f"定時投稿エラー ({time_key}): {e}")
