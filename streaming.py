"""
WebSocketストリーミングモジュール
Misskeyからリアルタイム通知を受信
"""

import logging
import asyncio
from typing import Optional
from mipac import Client
from mipac.models.notification import NotificationFollow, NotificationReaction, NotificationReply

logger = logging.getLogger(__name__)


class StreamingManager:
    """WebSocketでMisskeyの通知をリアルタイム受信"""
    
    def __init__(self, client: Client):
        self.client = client
        self.running = False
        self.stream_task: Optional[asyncio.Task] = None
        
        # コールバック関数
        self.on_follow_callback = None
        self.on_reply_callback = None
    
    def on_follow(self, callback):
        """フォロー通知のコールバック設定"""
        self.on_follow_callback = callback
        return callback
    
    def on_reply(self, callback):
        """リプライ通知のコールバック設定"""
        self.on_reply_callback = callback
        return callback
    
    async def start(self):
        """ストリーミング開始"""
        if self.running:
            logger.warning("ストリーミングは既に実行中です")
            return
        
        self.running = True
        logger.info("WebSocketストリーミング開始")
        
        try:
            # mainストリームに接続
            async with self.client.stream.main_stream() as stream:
                logger.info("mainストリームに接続しました")
                
                async for notification in stream:
                    if not self.running:
                        break
                    
                    await self._handle_notification(notification)
                    
        except Exception as e:
            logger.error(f"ストリーミングエラー: {e}", exc_info=True)
            self.running = False
            
            # 再接続を試みる
            if self.running:
                logger.info("5秒後に再接続を試みます...")
                await asyncio.sleep(5)
                await self.start()
    
    async def _handle_notification(self, notification):
        """通知を処理"""
        try:
            # フォロー通知
            if notification.type == "follow":
                logger.info(f"フォロー通知受信: @{notification['user'].username}")
                if self.on_follow_callback:
                    await self.on_follow_callback(notification)
            
            # リプライ通知
            elif notification.type == "reply":
                logger.info(f"リプライ通知受信: @{notification['user'].username}")
                if self.on_reply_callback:
                    await self.on_reply_callback(notification)
            
            # メンション通知
            elif notification.type == "mention":
                logger.info(f"メンション通知受信: @{notification['user'].username}")
                # メンションもリプライとして扱う
                if self.on_reply_callback:
                    await self.on_reply_callback(notification)
        
        except Exception as e:
            logger.error(f"通知処理エラー: {e}", exc_info=True)
    
    async def stop(self):
        """ストリーミング停止"""
        logger.info("WebSocketストリーミング停止")
        self.running = False
        
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
