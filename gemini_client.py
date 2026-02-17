"""
Gemini APIクライアント (新ライブラリ版)
google.genai を使用 (google.generativeai からの移行)
"""

import logging
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        """Gemini API クライアント初期化"""
        # API クライアント作成
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        # モデル名
        self.model_name = "gemini-2.5-flash"
        
        # キャラクタープロンプトを読み込み
        self.character_prompt = self._load_character_prompt()
        
        logger.info(f"✅ Gemini APIクライアント初期化完了 ({self.model_name})")
        logger.info(f"📝 キャラクタープロンプト: {len(self.character_prompt)} 文字読み込み")
    
    def _load_character_prompt(self) -> str:
        """キャラクタープロンプトをファイルから読み込み"""
        try:
            with open("katariina_prompt.md", "r", encoding="utf-8") as f:
                prompt = f.read()
            logger.debug("キャラクタープロンプト読み込み成功")
            return prompt
        except Exception as e:
            logger.error(f"キャラクタープロンプト読み込みエラー: {e}")
            return "あなたは親しみやすいキャラクターです。"
    
    async def generate_random_post(self) -> str:
        """
        ランダム投稿を生成
        :return: 投稿テキスト (140文字以内) または None (エラー時)
        """
        try:
            # ユーザープロンプト (system_instruction とは別)
            user_prompt = """以下の条件で、Misskeyに投稿する独り言を生成してください:
- 140文字以内
- キャラクターらしい自然な口調
- 日常的な内容、気分、考えていること
- 絵文字を適度に使用
- 返信ではなく、独立した投稿

投稿内容のみを出力してください（説明や前置きは不要）:"""

            # GenerateContentConfig を使用 (system_instruction として設定)
            config = types.GenerateContentConfig(
                system_instruction=self.character_prompt,  # ← システムインストラクションとして設定
                temperature=1.0,
                max_output_tokens=200
            )
            
            # generate_content を使用
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,  # ← ユーザープロンプトのみ
                config=config
            )
            
            # テキスト取得
            content = response.text.strip()
            
            # 140文字超過チェック
            if len(content) > 140:
                content = content[:140]
                logger.warning(f"生成テキストが140文字を超過: 切り詰めました")
            
            logger.info(f"✅ ランダム投稿生成成功: {content[:50]}...")
            return content
            
        except Exception as e:
            logger.error(f"❌ Gemini API エラー (ランダム投稿): {e}")
            return None
    
    async def generate_reply(self, user_message: str, username: str) -> str:
        """
        リプライを生成
        :param user_message: ユーザーのメッセージ
        :param username: ユーザー名
        :return: リプライテキスト (140文字以内) または None (エラー時)
        """
        try:
            # ユーザープロンプト
            user_prompt = f"""@{username} さんからのメンション:
「{user_message}」

以下の条件で返信を生成してください:
- 140文字以内
- キャラクターらしい自然な口調
- メッセージ内容に適切に応答
- 親しみやすく、ポジティブな返信
- 絵文字を適度に使用

返信内容のみを出力してください（説明や前置きは不要）:"""

            # GenerateContentConfig を使用 (system_instruction として設定)
            config = types.GenerateContentConfig(
                system_instruction=self.character_prompt,  # ← システムインストラクション
                temperature=1.0,
                max_output_tokens=200
            )
            
            # generate_content を使用
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            # テキスト取得
            content = response.text.strip()
            
            # 140文字超過チェック
            if len(content) > 140:
                content = content[:140]
                logger.warning(f"生成テキストが140文字を超過: 切り詰めました")
            
            logger.info(f"✅ リプライ生成成功: {content[:50]}...")
            return content
            
        except Exception as e:
            logger.error(f"❌ Gemini API エラー (リプライ): {e}")
            return None
