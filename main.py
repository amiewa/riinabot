"""
Misskeybot りいなちゃん - メインプログラム
Phase 3.2: NGWordManager 統合版
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import settings, bot_config
from database import Database
from misskey_client import MisskeyClient
from gemini_client import GeminiClient
from post_manager import PostManager
from scheduled_post_manager import ScheduledPostManager
from follow_manager import FollowManager
from reply_manager import ReplyManager
from streaming_manager import StreamingManager
from database_maintenance import DatabaseMaintenance
from log_maintenance import LogMaintenance
from timeline_post_manager import TimelinePostManager

# ログ設定
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RiinaBot:
    def __init__(self):
        """Bot初期化"""
        self.db = Database()
        self.misskey = MisskeyClient()
        self.gemini = GeminiClient()
        
        self.post_manager = PostManager(self.misskey, self.gemini, self.db)
        self.scheduled_post_manager = ScheduledPostManager(self.misskey, self.gemini, self.db)
        self.follow_manager = FollowManager(self.misskey, self.db)
        self.reply_manager = ReplyManager(self.misskey, self.gemini, self.db)
        self.timeline_post_manager = TimelinePostManager(self.misskey, self.gemini, self.db)
        
        # WebSocketストリーミング
        self.streaming_manager = StreamingManager(
            self.misskey,
            reply_manager=self.reply_manager,
            follow_manager=self.follow_manager
        )
        
        # メンテナンス
        self.db_maintenance = DatabaseMaintenance(self.db)
        self.log_maintenance = LogMaintenance()
        
        self.scheduler = AsyncIOScheduler()
        self.running = False
    
    async def initialize(self):
        """非同期初期化"""
        await self.db.connect()
        await self.misskey.connect()
        
        # ★ タイムライン連動投稿の初期化（外部NGワード読み込み）
        await self.timeline_post_manager.initialize()
        
        logger.info("=== りいなちゃんbot 起動 (Phase 3.2: NGWord Manager) ===")
    
    async def setup_scheduler(self):
        """スケジューラー設定"""
        # ランダム投稿
        random_post_enabled = bot_config.get("posting.random_post.enabled", True)
        if random_post_enabled:
            interval_minutes = bot_config.get("posting.random_post.interval_minutes", 60)
            self.scheduler.add_job(
                self.post_manager.post_random,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='random_post',
                name='ランダム投稿'
            )
            logger.info(f"✅ ランダム投稿: {interval_minutes}分ごと")
        else:
            logger.info("⏸️  ランダム投稿: 無効")
        
        # タイムライン連動投稿
        timeline_post_enabled = bot_config.get("posting.timeline_post.enabled", False)
        if timeline_post_enabled:
            interval_minutes = bot_config.get("posting.timeline_post.interval_minutes", 30)
            self.scheduler.add_job(
                self.timeline_post_manager.post_timeline_based,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='timeline_post',
                name='タイムライン連動投稿'
            )
            source = bot_config.get("posting.timeline_post.source", "home")
            logger.info(f"✅ タイムライン連動投稿: {interval_minutes}分ごと (対象: {source})")
        else:
            logger.info("⏸️  タイムライン連動投稿: 無効")
        
        # フォロー状態チェック
        follow_check_interval = bot_config.get("follow.check_interval_minutes", 30)
        self.scheduler.add_job(
            self.follow_manager.check_and_sync_followers,
            trigger=IntervalTrigger(minutes=follow_check_interval),
            id='follow_check',
            name='フォロー状態チェック (定期同期)'
        )
        logger.info(f"✅ フォロー状態チェック: {follow_check_interval}分ごと (定期同期)")
        
        # 定時投稿
        scheduled_posts_enabled = bot_config.get("posting.scheduled_posts.enabled", True)
        if scheduled_posts_enabled:
            scheduled_posts_config = bot_config.get("posting.scheduled_posts.posts", {})
            
            if isinstance(scheduled_posts_config, dict):
                time_keys = scheduled_posts_config.keys()
            elif isinstance(scheduled_posts_config, list):
                scheduled_posts_config = {
                    item["time"]: item.get("messages", [])
                    for item in scheduled_posts_config
                    if "time" in item
                }
                time_keys = scheduled_posts_config.keys()
            else:
                logger.warning(f"定時投稿設定が不正な形式: {type(scheduled_posts_config)}")
                time_keys = []
            
            for time_key in time_keys:
                try:
                    hour, minute = time_key.split(":")
                    self.scheduler.add_job(
                        lambda tk=time_key: self.scheduled_post_manager.post_scheduled(tk),
                        trigger=CronTrigger(hour=hour, minute=minute),
                        id=f'scheduled_{time_key}',
                        name=f'定時投稿 {time_key}'
                    )
                    logger.info(f"✅ 定時投稿設定: {time_key}")
                except Exception as e:
                    logger.error(f"定時投稿設定エラー ({time_key}): {e}")
        else:
            logger.info("⏸️  定時投稿: 無効")
        
        # メンテナンスジョブ
        maintenance_enabled = bot_config.get("maintenance.enabled", True)
        if maintenance_enabled:
            cleanup_time = bot_config.get("maintenance.cleanup_time", "03:00")
            cleanup_days = bot_config.get("maintenance.cleanup_days", 30)
            hour, minute = cleanup_time.split(":")
            self.scheduler.add_job(
                lambda: self.db_maintenance.cleanup_old_records(cleanup_days),
                trigger=CronTrigger(hour=hour, minute=minute),
                id='db_cleanup',
                name='DB古いレコード削除'
            )
            logger.info(f"✅ DB古いレコード削除: 毎日{cleanup_time} (>{cleanup_days}日前)")
            
            backup_time = bot_config.get("maintenance.backup_time", "04:00")
            backup_compress = bot_config.get("maintenance.backup_compress", True)
            keep_backups = bot_config.get("maintenance.keep_backups", 7)
            hour, minute = backup_time.split(":")
            
            async def backup_and_cleanup():
                await self.db_maintenance.backup_database(compress=backup_compress)
                await self.db_maintenance.cleanup_old_backups(keep_count=keep_backups)
            
            self.scheduler.add_job(
                backup_and_cleanup,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='db_backup',
                name='DBバックアップ'
            )
            logger.info(f"✅ DBバックアップ: 毎日{backup_time} (最新{keep_backups}個保持)")
            
            log_rotate_time = bot_config.get("maintenance.log_rotate_time", "05:00")
            log_cleanup_days = bot_config.get("maintenance.log_cleanup_days", 30)
            hour, minute = log_rotate_time.split(":")
            
            def log_rotate_and_cleanup():
                self.log_maintenance.rotate_log("bot.log")
                self.log_maintenance.cleanup_old_logs(days=log_cleanup_days)
            
            self.scheduler.add_job(
                log_rotate_and_cleanup,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='log_maintenance',
                name='ログローテーション'
            )
            logger.info(f"✅ ログローテーション: 毎日{log_rotate_time} (>{log_cleanup_days}日前削除)")
            
            stats_time = bot_config.get("maintenance.stats_time", "06:00")
            hour, minute = stats_time.split(":")
            
            async def log_all_stats():
                await self.db_maintenance.log_database_stats()
                self.log_maintenance.log_stats()
            
            self.scheduler.add_job(
                log_all_stats,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='stats',
                name='統計情報'
            )
            logger.info(f"✅ 統計情報: 毎日{stats_time}")
        else:
            logger.info("⏸️  メンテナンス: 無効")
        
        self.scheduler.start()
        logger.info("=== スケジューラー起動完了 ===")
    
    async def start(self):
        """Bot起動"""
        self.running = True
        await self.initialize()
        await self.setup_scheduler()
        
        await self.db_maintenance.log_database_stats()
        self.log_maintenance.log_stats()
        
        await self.streaming_manager.start()
        logger.info("✅ WebSocketリアルタイム監視: メンション・フォロー通知")
        logger.info("=== Bot起動完了 ===")
        
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.stop())
            )
        
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Bot停止"""
        logger.info("Bot停止中...")
        self.running = False
        
        logger.info("停止時バックアップを作成中...")
        await self.db_maintenance.backup_database(compress=True)
        
        await self.streaming_manager.stop()
        
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        await self.misskey.close()
        await self.db.close()
        logger.info("Bot停止完了")

async def main():
    bot = RiinaBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt検出")
    except Exception as e:
        logger.exception(f"予期しないエラー: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    runner = asyncio.Runner()
    runner.run(main())
