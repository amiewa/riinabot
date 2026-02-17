"""
ログメンテナンスモジュール
ログファイルのローテーション・圧縮・削除
"""

import logging
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class LogMaintenance:
    def __init__(self, log_dir: str = "logs"):
        """
        :param log_dir: ログディレクトリパス
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
    
    def rotate_log(self, log_filename: str = "bot.log"):
        """
        ログファイルをローテーション (リネーム + 圧縮)
        :param log_filename: ローテーション対象のログファイル名
        """
        logger.info(f"🔄 ログローテーション開始: {log_filename}")
        
        try:
            log_file = self.log_dir / log_filename
            
            if not log_file.exists():
                logger.warning(f"ログファイルが見つかりません: {log_file}")
                return
            
            # ファイルサイズチェック
            size_mb = log_file.stat().st_size / (1024 * 1024)
            logger.info(f"  - 現在のサイズ: {size_mb:.2f}MB")
            
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_filename = f"{log_file.stem}_{timestamp}{log_file.suffix}"
            rotated_path = self.log_dir / rotated_filename
            
            # リネーム
            shutil.move(log_file, rotated_path)
            logger.info(f"  - ローテーション: {rotated_filename}")
            
            # gzip圧縮
            compressed_path = rotated_path.with_suffix(f"{rotated_path.suffix}.gz")
            with open(rotated_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 元のファイルを削除
            rotated_path.unlink()
            
            compressed_size_mb = compressed_path.stat().st_size / (1024 * 1024)
            compression_ratio = (1 - compressed_size_mb / size_mb) * 100
            
            logger.info(f"  - 圧縮完了: {compressed_path.name}")
            logger.info(f"  - 圧縮率: {compression_ratio:.1f}% ({size_mb:.2f}MB → {compressed_size_mb:.2f}MB)")
            logger.info(f"✅ ログローテーション完了")
            
        except Exception as e:
            logger.error(f"ログローテーションエラー: {e}")
    
    def cleanup_old_logs(self, days: int = 30, pattern: str = "bot_*.log.gz"):
        """
        古いログファイルを削除
        :param days: 何日以前のログを削除するか
        :param pattern: 削除対象ファイルのパターン
        """
        logger.info(f"🗑️  古いログ削除開始 (>{days}日前)")
        
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            deleted_count = 0
            deleted_size = 0
            
            for log_file in self.log_dir.glob(pattern):
                # ファイルの更新日時をチェック
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if mtime < cutoff_time:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    logger.info(f"  - 削除: {log_file.name} ({size / 1024:.1f}KB)")
                    deleted_count += 1
                    deleted_size += size
            
            if deleted_count > 0:
                logger.info(f"✅ 古いログ削除完了: {deleted_count}件 ({deleted_size / (1024 * 1024):.2f}MB)")
            else:
                logger.info("  - 削除対象なし")
                
        except Exception as e:
            logger.error(f"古いログ削除エラー: {e}")
    
    def get_log_stats(self) -> dict:
        """
        ログディレクトリの統計情報を取得
        :return: 統計情報の辞書
        """
        try:
            stats = {
                'total_files': 0,
                'total_size_mb': 0,
                'active_log_size_mb': 0,
                'archived_count': 0,
                'archived_size_mb': 0
            }
            
            # 全ログファイルを走査
            for log_file in self.log_dir.glob("*"):
                if not log_file.is_file():
                    continue
                
                size_mb = log_file.stat().st_size / (1024 * 1024)
                stats['total_files'] += 1
                stats['total_size_mb'] += size_mb
                
                # アクティブログ
                if log_file.name == "bot.log":
                    stats['active_log_size_mb'] = size_mb
                
                # アーカイブログ
                if log_file.suffix == ".gz":
                    stats['archived_count'] += 1
                    stats['archived_size_mb'] += size_mb
            
            return stats
            
        except Exception as e:
            logger.error(f"ログ統計情報取得エラー: {e}")
            return {}
    
    def log_stats(self):
        """ログ統計情報をログ出力"""
        stats = self.get_log_stats()
        
        if not stats:
            logger.warning("ログ統計情報の取得に失敗しました")
            return
        
        logger.info("📊 ログ統計情報:")
        logger.info(f"  - 総ファイル数: {stats['total_files']}個")
        logger.info(f"  - 総サイズ: {stats['total_size_mb']:.2f}MB")
        logger.info(f"  - アクティブログ: {stats['active_log_size_mb']:.2f}MB")
        logger.info(f"  - アーカイブログ: {stats['archived_count']}個 ({stats['archived_size_mb']:.2f}MB)")
