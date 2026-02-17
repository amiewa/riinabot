"""
Gemini APIクライアント (新ライブラリ版 - MAX_TOKENS 問題修正版)
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
                system_instruction=self.character_prompt,
                temperature=1.0,
                max_output_tokens=1024  # ← 512→1024 に増量（日本語は1文字=4〜5トークン）
            )
            
            # generate_content を使用
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            # finish_reason チェック
            if response.candidates and response.candidates[0].finish_reason != types.FinishReason.STOP:
                logger.warning(f"⚠️ finish_reason: {response.candidates[0].finish_reason}")
            
            # テキスト取得
            content = response.text.strip()
            
            # 改行削除
            if '\n' in content:
                content = content.replace('\n', ' ').replace('  ', ' ')
            
            # 140文字超過チェック
            if len(content) > 140:
                logger.info(f"📏 {len(content)}文字を140文字に切り詰め")
                content = content[:140]
            
            logger.info(f"✅ ランダム投稿生成成功 ({len(content)}文字): {content}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Gemini API エラー (ランダム投稿): {e}")
            logger.exception("詳細:")
            return None
    
    async def generate_reply(self, user_message: str, username: str) -> str:
        """
        リプライを生成
        :param user_message: ユーザーのメッセージ
        :param username: ユーザー名
        :return: リプライテキスト (140文字以内) または None (エラー時)
        """
        try:
            # ユーザープロンプト (短すぎるのを防ぐため、目安を明示)
            user_prompt = f"""@{username} さんからのメンション:
「{user_message}」

以下の条件で返信を生成してください:
- 50〜120文字程度 (短すぎず、長すぎず)
- キャラクターらしい自然な口調
- メッセージ内容に適切に応答
- 親しみやすく、ポジティブな返信
- 絵文字は控えめに (プロンプトのルールに従う)

返信内容のみを出力してください（説明や前置きは不要）:"""

            # GenerateContentConfig を使用 (system_instruction として設定)
            config = types.GenerateContentConfig(
                system_instruction=self.character_prompt,
                temperature=1.0,
                max_output_tokens=1024,  # ← 512→1024 に増量
                candidate_count=1
            )
            
            # generate_content を使用
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config
            )
            
            # finish_reason チェック
            if response.candidates:
                finish_reason = response.candidates[0].finish_reason
                if finish_reason != types.FinishReason.STOP:
                    logger.warning(f"⚠️ finish_reason: {finish_reason} (MAX_TOKENSの可能性)")
            
            # テキスト取得
            content = response.text.strip()
            
            # 改行削除
            if '\n' in content:
                content = content.replace('\n', ' ').replace('  ', ' ')
            
            # 140文字超過チェック
            if len(content) > 140:
                logger.info(f"📏 {len(content)}文字を140文字に切り詰め")
                content = content[:140]
            
            logger.info(f"✅ リプライ生成成功 ({len(content)}文字): {content}")
            return content
            
        except Exception as e:
            logger.error(f"❌ Gemini API エラー (リプライ): {e}")
            logger.exception("詳細エラー:")
            return None
