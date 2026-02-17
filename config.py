"""
設定管理モジュール
環境変数とYAML設定ファイルを読み込む
"""

import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """環境変数の設定"""
    misskey_instance_url: str = Field(..., alias="MISSKEY_INSTANCE_URL")
    misskey_api_token: str = Field(..., alias="MISSKEY_API_TOKEN")
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    timezone: str = Field("Asia/Tokyo", alias="TIMEZONE")
    database_path: str = Field("data/riina_bot.db", alias="DATABASE_PATH")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class BotConfig:
    """YAML設定ファイルの管理"""
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """YAMLファイルを読み込む"""
        if not Path(self.config_path).exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def get(self, key_path: str, default=None):
        """
        ドット記法で設定値を取得
        例: get("posting.night_mode.enabled")
        """
        keys = key_path.split(".")
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def load_character_prompt(self):
        """キャラクタープロンプトファイルを読み込む"""
        prompt_file = self.get("bot.character_prompt_file", "katariina_prompt.md")
        
        if not Path(prompt_file).exists():
            raise FileNotFoundError(f"プロンプトファイルが見つかりません: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()


# グローバル設定インスタンス
settings = Settings()
bot_config = BotConfig()
