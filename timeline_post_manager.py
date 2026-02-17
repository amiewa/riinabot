"""
タイムライン連動投稿マネージャー
タイムラインからキーワードを抽出し、それを使った投稿を自動生成
"""

import logging
import re
import random
from datetime import datetime
from typing import List, Optional, Dict, Any

from config import bot_config

logger = logging.getLogger(__name__)

class TimelinePostManager:
    def __init__(self, misskey, gemini, db):
        """
        :param misskey: MisskeyClient インスタンス
        :param gemini: GeminiClient インスタンス
        :param db: Database インスタンス
        """
        self.misskey = misskey
        self.gemini = gemini
        self.db = db
        
        # 設定読み込み
        self.enabled = bot_config.get("posting.timeline_post.enabled", False)
        self.source = bot_config.get("posting.timeline_post.source", "home")
        self.ng_words = bot_config.get("posting.timeline_post.ng_words", [])
        self.min_keyword_length = bot_config.get("posting.timeline_post.min_keyword_length", 2)
        self.max_notes_fetch = bot_config.get("posting.timeline_post.max_notes_fetch", 20)
        
        # 夜間投稿停止設定
        self.night_mode_enabled = bot_config.get("posting.night_mode.enabled", True)
        self.night_start = bot_config.get("posting.night_mode.start_hour", 23)
        self.night_end = bot_config.get("posting.night_mode.end_hour", 5)
        
        logger.info(f"📡 タイムライン連動投稿: {'有効' if self.enabled else '無効'}")
        if self.enabled:
            logger.info(f"📡 対象タイムライン: {self.source}")
            logger.info(f"📡 NGワード: {len(self.ng_words)}件")
    
    def _is_night_time(self) -> bool:
        """現在が夜間時間帯か判定"""
        if not self.night_mode_enabled:
            return False
        
        now = datetime.now()
        current_hour = now.hour
        
        if self.night_start < self.night_end:
            return self.night_start <= current_hour < self.night_end
        else:
            return current_hour >= self.night_start or current_hour < self.night_end
    
    async def fetch_timeline_notes(self) -> List[Dict[str, Any]]:
        """
        タイムラインから最新のノートを取得
        :return: ノートのリスト
        """
        try:
            if self.source == "home":
                endpoint = "notes/timeline"
            elif self.source == "local":
                endpoint = "notes/local-timeline"
            elif self.source == "global":
                endpoint = "notes/global-timeline"
            else:
                logger.error(f"不正なタイムラインソース: {self.source}")
                return []
            
            # Misskey API でタイムライン取得
            notes = self.misskey.client.request(
                endpoint,
                json={"limit": self.max_notes_fetch}
            )
            
            if not notes:
                logger.warning(f"タイムライン取得結果が空: {self.source}")
                return []
            
            logger.info(f"✅ タイムライン取得成功: {len(notes)}件 ({self.source})")
            return notes
            
        except Exception as e:
            logger.error(f"タイムライン取得エラー: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """
        テキストをクリーニング（URL、メンション、絵文字を削除）
        :param text: 元のテキスト
        :return: クリーニング後のテキスト
        """
        # URL削除
        text = re.sub(r'https?://[^\s]+', '', text)
        
        # メンション削除 (@username)
        text = re.sub(r'@[a-zA-Z0-9_]+', '', text)
        
        # カスタム絵文字削除 (:emoji_name:)
        text = re.sub(r':[a-zA-Z0-9_]+:', '', text)
        
        # 改行・余分な空白を整理
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _contains_ng_word(self, text: str) -> bool:
        """
        NGワードが含まれているかチェック
        :param text: チェック対象テキスト
        :return: NGワードが含まれていたら True
        """
        for ng_word in self.ng_words:
            if ng_word.lower() in text.lower():
                return True
        return False
    
    def _extract_keywords(self, notes: List[Dict[str, Any]]) -> List[str]:
        """
        ノートリストからキーワードを抽出
        :param notes: ノートのリスト
        :return: 抽出されたキーワードのリスト
        """
        keywords = []
        
        for note in notes:
            text = note.get("text", "")
            if not text:
                continue
            
            # テキストクリーニング
            cleaned_text = self._clean_text(text)
            
            # NGワードチェック
            if self._contains_ng_word(cleaned_text):
                continue
            
            # 短すぎるテキストはスキップ
            if len(cleaned_text) < self.min_keyword_length:
                continue
            
            # シンプルに単語分割（空白区切り）
            words = cleaned_text.split()
            
            for word in words:
                # 最小文字数チェック
                if len(word) >= self.min_keyword_length:
                    # NGワードチェック
                    if not self._contains_ng_word(word):
                        keywords.append(word)
        
        # 重複削除
        keywords = list(set(keywords))
        
        logger.info(f"🔍 キーワード抽出: {len(keywords)}個")
        return keywords
    
    async def generate_post_from_keyword(self, keyword: str) -> Optional[str]:
        """
        キーワードを使って投稿文を生成
        :param keyword: キーワード
        :return: 生成された投稿文 または None
        """
        try:
            # Gemini に投稿生成を依頼
            prompt = f"""タイムラインで見かけたキーワード「{keyword}」について、
りいなちゃんらしい独り言を生成してください。

以下の条件を守ってください:
- 140文字以内
- キーワードに対する感想・コメント
- 誰かに話しかけているわけではない独り言トーン
- 自然でキャラクターらしい口調

投稿内容のみを出力してください（説明や前置きは不要）:"""

            # Gemini API 呼び出し（system_instruction はすでに設定済み）
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=self.gemini.character_prompt,
                temperature=1.0,
                max_output_tokens=1024
            )
            
            response = self.gemini.client.models.generate_content(
                model=self.gemini.model_name,
                contents=prompt,
                config=config
            )
            
            content = response.text.strip()
            
            # 改行削除
            if '\n' in content:
                content = content.replace('\n', ' ').replace('  ', ' ')
            
            # 140文字制限
            if len(content) > 140:
                content = content[:140]
            
            logger.info(f"✅ タイムライン連動投稿生成成功 ({len(content)}文字): {content}")
            return content
            
        except Exception as e:
            logger.error(f"タイムライン連動投稿生成エラー: {e}")
            return None
    
    async def post_timeline_based(self):
        """
        タイムライン連動投稿を実行
        """
        if not self.enabled:
            logger.debug("タイムライン連動投稿: 無効")
            return
        
        # 夜間チェック
        if self._is_night_time():
            logger.info("🌙 夜間モード: タイムライン連動投稿をスキップ")
            return
        
        try:
            # タイムライン取得
            notes = await self.fetch_timeline_notes()
            
            if not notes:
                logger.warning("タイムラインが空: 投稿をスキップ")
                return
            
            # キーワード抽出
            keywords = self._extract_keywords(notes)
            
            if not keywords:
                logger.warning("キーワードが抽出できませんでした")
                return
            
            # ランダムにキーワードを選択
            keyword = random.choice(keywords)
            logger.info(f"📝 選択されたキーワード: {keyword}")
            
            # 投稿文生成
            post_content = await self.generate_post_from_keyword(keyword)
            
            if not post_content:
                logger.error("投稿文の生成に失敗しました")
                return
            
            # 投稿実行
            note_id = await self.misskey.send_note(post_content)
            
            if note_id:
                # データベースに記録
                await self.db.add_post(note_id, "timeline", post_content)
                logger.info(f"✅ タイムライン連動投稿完了: {post_content[:50]}...")
            else:
                logger.error("投稿の送信に失敗しました")
        
        except Exception as e:
            logger.error(f"タイムライン連動投稿エラー: {e}")
            logger.exception("詳細:")
