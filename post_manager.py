"""
投稿管理モジュール
ランダム投稿・夜間停止機能
"""

import logging
from datetime import datetime
import pytz
from misskey_client import MisskeyClient
from gemini_client import GeminiClient
from database import Database
from config import bot_config

logger = logging.getLogger(__name__)

class PostManager:
    def __init__(self, misskey: MisskeyClient, gemini: GeminiClient, db: Database):
        """
        :param misskey: Misskeyクライアント
        :param gemini: Geminiクライアント
        :param db: データベース
        """
        self.misskey = misskey
        self.gemini = gemini
        self.db = db
        
        # 夜間モード設定
        self.night_mode_enabled = bot_config.get("posting.night_mode.enabled", True)
        self.night_start_hour = bot_config.get("posting.night_mode.start_hour", 23)
        self.night_end_hour = bot_config.get("posting.night_mode.end_hour", 5)
        
        # タイムゾーン
        self.timezone = pytz.timezone(bot_config.get("settings.timezone", "Asia/Tokyo"))
    
    def is_night_time(self) -> bool:
        """夜間時間帯かチェック"""
        if not self.night_mode_enabled:
            return False
        
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # 23:00-05:00 のような跨ぎ判定
        if self.night_start_hour > self.night_end_hour:
            return current_hour >= self.night_start_hour or current_hour < self.night_end_hour
        else:
            return self.night_start_hour <= current_hour < self.night_end_hour
    
    async def post_random(self):
        """ランダム投稿実行"""
        if self.is_night_time():
            logger.info("🌙 夜間モード: 投稿スキップ")
            return
        
        try:
            # Geminiでランダム投稿生成
            content = await self.gemini.generate_random_post()
            
            if content is None:
                logger.warning("⏸️  Gemini APIエラー: 投稿スキップ")
                return
            
            # Misskeyに投稿
            note = await self.misskey.post_note(content)
            note_id = note.get('createdNote', {}).get('id', 'unknown')
            
            # データベースに記録
            await self.db.add_post(note_id, "random", content)
            
            logger.info(f"✅ ランダム投稿成功: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"ランダム投稿エラー: {e}")
