"""
データベースメンテナンスモジュール
古いレコードの削除・バックアップ機能
"""

import logging
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from database import Database
from config import settings

logger = logging.getLogger(__name__)

class DatabaseMaintenance:
    def __init__(self, db: Database):
        """
        :param db: データベースインスタンス
        """
        self.db = db
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    async def cleanup_old_records(self, days: int = 30):
        """
        古いレコードを削除
        :param days: 何日以前のレコードを削除するか (デフォルト30日)
        """
        logger.info(f"🗑️  古いレコード削除開始 (>{days}日前)")
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 投稿履歴の削除
            async with self.db.db.execute(
                "DELETE FROM posts WHERE posted_at < ?",
                (cutoff_date,)
            ) as cursor:
                await self.db.db.commit()
                deleted_posts = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                logger.info(f"  - 投稿履歴削除: {deleted_posts}件")
            
            # レート制限レコードの削除
            async with self.db.db.execute(
                "DELETE FROM reply_rate_limits WHERE replied_at < ?",
                (cutoff_date,)
            ) as cursor:
                await self.db.db.commit()
                deleted_rate_limits = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                logger.info(f"  - レート制限レコード削除: {deleted_rate_limits}件")
            
            # VACUUM実行 (データベースファイルを最適化)
            await self.db.db.execute("VACUUM")
            logger.info("  - データベース最適化完了 (VACUUM)")
            
            logger.info(f"✅ 古いレコード削除完了: 投稿{deleted_posts}件, レート制限{deleted_rate_limits}件")
            
        except Exception as e:
            logger.error(f"古いレコード削除エラー: {e}")
    
    async def backup_database(self, compress: bool = True):
        """
        データベースをバックアップ
        :param compress: gzip圧縮するか (デフォルトTrue)
        :return: バックアップファイルパス
        """
        logger.info("💾 データベースバックアップ開始")
        
        try:
            # バックアップファイル名 (タイムスタンプ付き)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"bot_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # データベースファイルをコピー
            db_path = Path(settings.database_path)
            if not db_path.exists():
                logger.error(f"データベースファイルが見つかりません: {db_path}")
                return None
            
            shutil.copy2(db_path, backup_path)
            logger.info(f"  - バックアップ作成: {backup_path}")
            
            # gzip圧縮
            if compress:
                compressed_path = backup_path.with_suffix('.db.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # 元のファイルを削除
                backup_path.unlink()
                
                # ファイルサイズ取得
                original_size = db_path.stat().st_size / 1024  # KB
                compressed_size = compressed_path.stat().st_size / 1024  # KB
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                logger.info(f"  - 圧縮完了: {compressed_path}")
                logger.info(f"  - 圧縮率: {compression_ratio:.1f}% ({original_size:.1f}KB → {compressed_size:.1f}KB)")
                
                backup_path = compressed_path
            else:
                size = backup_path.stat().st_size / 1024  # KB
                logger.info(f"  - サイズ: {size:.1f}KB")
            
            logger.info(f"✅ データベースバックアップ完了: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"データベースバックアップエラー: {e}")
            return None
    
    async def cleanup_old_backups(self, keep_count: int = 7):
        """
        古いバックアップファイルを削除
        :param keep_count: 保持するバックアップ数 (デフォルト7個)
        """
        logger.info(f"🗑️  古いバックアップ削除開始 (最新{keep_count}個を保持)")
        
        try:
            # バックアップファイル一覧を取得 (作成日時順)
            backup_files = sorted(
                self.backup_dir.glob("bot_backup_*.db*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # 保持数を超えたファイルを削除
            deleted_count = 0
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                logger.info(f"  - 削除: {backup_file.name}")
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"✅ 古いバックアップ削除完了: {deleted_count}件")
            else:
                logger.info("  - 削除対象なし")
                
        except Exception as e:
            logger.error(f"古いバックアップ削除エラー: {e}")
    
    async def get_database_stats(self) -> dict:
        """
        データベース統計情報を取得
        :return: 統計情報の辞書
        """
        try:
            stats = {}
            
            # フォロワー数
            async with self.db.db.execute("SELECT COUNT(*) FROM followers") as cursor:
                result = await cursor.fetchone()
                stats['followers_count'] = result[0] if result else 0
            
            # 投稿数
            async with self.db.db.execute("SELECT COUNT(*) FROM posts") as cursor:
                result = await cursor.fetchone()
                stats['posts_count'] = result[0] if result else 0
            
            # レート制限レコード数
            async with self.db.db.execute("SELECT COUNT(*) FROM reply_rate_limits") as cursor:
                result = await cursor.fetchone()
                stats['rate_limit_records'] = result[0] if result else 0
            
            # データベースファイルサイズ
            db_path = Path(settings.database_path)
            if db_path.exists():
                stats['db_size_kb'] = db_path.stat().st_size / 1024
            else:
                stats['db_size_kb'] = 0
            
            # 最古・最新の投稿日時
            async with self.db.db.execute(
                "SELECT MIN(posted_at), MAX(posted_at) FROM posts"
            ) as cursor:
                result = await cursor.fetchone()
                if result and result[0]:
                    stats['oldest_post'] = result[0]
                    stats['newest_post'] = result[1]
                else:
                    stats['oldest_post'] = None
                    stats['newest_post'] = None
            
            return stats
            
        except Exception as e:
            logger.error(f"データベース統計情報取得エラー: {e}")
            return {}
    
    async def log_database_stats(self):
        """データベース統計情報をログ出力"""
        stats = await self.get_database_stats()
        
        if not stats:
            logger.warning("データベース統計情報の取得に失敗しました")
            return
        
        logger.info("📊 データベース統計情報:")
        logger.info(f"  - フォロワー数: {stats.get('followers_count', 0)}人")
        logger.info(f"  - 投稿履歴: {stats.get('posts_count', 0)}件")
        logger.info(f"  - レート制限レコード: {stats.get('rate_limit_records', 0)}件")
        logger.info(f"  - データベースサイズ: {stats.get('db_size_kb', 0):.2f}KB")
        
        if stats.get('oldest_post'):
            logger.info(f"  - 最古の投稿: {stats['oldest_post'][:19]}")
            logger.info(f"  - 最新の投稿: {stats['newest_post'][:19]}")
