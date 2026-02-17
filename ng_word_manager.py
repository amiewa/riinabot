"""
NGワード管理モジュール
config.yaml と 外部URLからNGワードを読み込む
"""

import logging
import aiohttp
from typing import List, Set
from config import bot_config

logger = logging.getLogger(__name__)

class NGWordManager:
    def __init__(self):
        """NGワードマネージャー初期化"""
        self.ng_words: Set[str] = set()
        self._load_ng_words()
    
    def _load_ng_words(self):
        """NGワードを読み込み（config.yaml + 外部URL）"""
        # config.yaml から読み込み
        config_ng_words = bot_config.get("posting.timeline_post.ng_words", [])
        self.ng_words.update(config_ng_words)
        logger.info(f"📋 config.yaml から NGワード読み込み: {len(config_ng_words)}件")
        
        # 外部URLリストを取得
        external_urls = bot_config.get("posting.timeline_post.ng_word_urls", [])
        if external_urls:
            logger.info(f"🌐 外部NGワードリスト: {len(external_urls)}個のURL")
    
    async def load_external_ng_words(self):
        """外部URLからNGワードを非同期で読み込み"""
        external_urls = bot_config.get("posting.timeline_post.ng_word_urls", [])
        
        if not external_urls:
            logger.info("外部NGワードURLが設定されていません")
            return
        
        for url in external_urls:
            try:
                logger.info(f"🌐 外部NGワードリスト取得中: {url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            content = await response.text()
                            # 改行区切りでNGワードを取得
                            words = [line.strip() for line in content.splitlines() if line.strip()]
                            
                            # 空行やコメント行を除外
                            words = [w for w in words if w and not w.startswith('#')]
                            
                            before_count = len(self.ng_words)
                            self.ng_words.update(words)
                            after_count = len(self.ng_words)
                            added_count = after_count - before_count
                            
                            logger.info(f"✅ 外部NGワード追加: {added_count}件 (合計: {after_count}件)")
                        else:
                            logger.warning(f"外部NGワードリスト取得失敗: HTTP {response.status}")
            
            except asyncio.TimeoutError:
                logger.error(f"外部NGワードリスト取得タイムアウト: {url}")
            except Exception as e:
                logger.error(f"外部NGワードリスト取得エラー: {url} - {e}")
        
        logger.info(f"📊 NGワード総数: {len(self.ng_words)}件")
    
    def contains_ng_word(self, text: str) -> bool:
        """
        テキストにNGワードが含まれているかチェック
        :param text: チェック対象テキスト
        :return: NGワードが含まれていたら True
        """
        text_lower = text.lower()
        for ng_word in self.ng_words:
            if ng_word.lower() in text_lower:
                return True
        return False
    
    def get_ng_word_count(self) -> int:
        """NGワードの総数を取得"""
        return len(self.ng_words)


# グローバルインスタンス
_ng_word_manager = None

def get_ng_word_manager() -> NGWordManager:
    """NGWordManager のシングルトンインスタンスを取得"""
    global _ng_word_manager
    if _ng_word_manager is None:
        _ng_word_manager = NGWordManager()
    return _ng_word_manager
