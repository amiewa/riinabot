"""
WebSocketストリーミング管理モジュール
リアルタイムメンション・フォロー通知対応
"""

import logging
import asyncio
import json
import websockets
from misskey_client import MisskeyClient
from config import settings

logger = logging.getLogger(__name__)

class StreamingManager:
    def __init__(self, misskey: MisskeyClient, reply_manager=None, follow_manager=None):
        """
        :param misskey: Misskeyクライアント
        :param reply_manager: ReplyManagerインスタンス (オプション)
        :param follow_manager: FollowManagerインスタンス (オプション)
        """
        self.misskey = misskey
        self.reply_manager = reply_manager
        self.follow_manager = follow_manager
        self.running = False
        self.stream_task = None
        self.ws = None
    
    async def start(self):
        """WebSocketストリーミング開始"""
        if self.running:
            logger.warning("ストリーミングは既に起動しています")
            return
        
        self.running = True
        self.stream_task = asyncio.create_task(self._connect_and_listen())
        logger.info("✅ WebSocketストリーミング開始")
    
    async def stop(self):
        """WebSocketストリーミング停止"""
        self.running = False
        
        if self.ws:
            await self.ws.close()
        
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocketストリーミング停止")
    
    async def _connect_and_listen(self):
        """WebSocket接続とイベントリスニング"""
        # Misskey WebSocket URL
        instance_url = settings.misskey_instance_url
        ws_url = instance_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/streaming'
        
        # クエリパラメータでトークン認証
        ws_url_with_token = f"{ws_url}?i={settings.misskey_api_token}"
        
        retry_count = 0
        max_retries = 5
        
        while self.running:
            try:
                logger.info(f"WebSocket接続試行: {ws_url}")
                
                # extra_headers を削除し、URLに直接トークンを含める
                async with websockets.connect(ws_url_with_token) as websocket:
                    self.ws = websocket
                    retry_count = 0  # 接続成功したらリトライカウントリセット
                    
                    # 接続確立後、チャンネル接続
                    await self._subscribe_channels(websocket)
                    
                    logger.info("✅ WebSocket接続成功")
                    
                    # メッセージ受信ループ
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON解析エラー: {e}")
                        except Exception as e:
                            logger.exception(f"メッセージ処理エラー: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket接続が切断されました")
            except Exception as e:
                logger.error(f"WebSocket接続エラー: {e}")
            
            # 再接続処理
            if self.running:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"WebSocket再接続失敗 ({max_retries}回): 停止します")
                    self.running = False
                    break
                
                wait_time = min(2 ** retry_count, 60)  # 指数バックオフ (最大60秒)
                logger.info(f"WebSocket再接続待機: {wait_time}秒")
                await asyncio.sleep(wait_time)
    
    async def _subscribe_channels(self, websocket):
        """チャンネル購読"""
        # mainストリームに接続
        connect_msg = {
            "type": "connect",
            "body": {
                "channel": "main",
                "id": "main"
            }
        }
        await websocket.send(json.dumps(connect_msg))
        logger.info("📡 mainストリームに接続")
    
    async def _handle_message(self, data: dict):
        """WebSocketメッセージ処理"""
        msg_type = data.get('type')
        body = data.get('body') or {}
        
        logger.debug(f"WebSocketメッセージ受信: type={msg_type}")
        
        # チャンネルイベント
        if msg_type == 'channel':
            channel_id = body.get('id')
            event_type = body.get('type')
            event_body = body.get('body') or {}
            
            if channel_id == 'main':
                await self._handle_main_event(event_type, event_body)
        
        # 接続完了
        elif msg_type == 'connected':
            logger.info("✅ チャンネル接続完了")
    
    async def _handle_main_event(self, event_type: str, event_body):
        """mainストリームイベント処理"""
        logger.debug(f"イベント受信: {event_type}")
        
        # event_body が None や非dict の場合を防御
        if not isinstance(event_body, dict):
            logger.warning(f"⚠️ event_body が不正 (type={type(event_body).__name__}, event={event_type}): {event_body}")
            return
        
        # メンション通知
        if event_type == 'mention':
            note = event_body
            if self.reply_manager:
                logger.info("🔔 メンション通知受信 (WebSocket)")
                await self.reply_manager.handle_mention(note)
        
        # リプライ通知
        elif event_type == 'reply':
            note = event_body
            if self.reply_manager:
                logger.info("🔔 リプライ通知受信 (WebSocket)")
                await self.reply_manager.handle_mention(note)
        
        # フォロー通知
        elif event_type == 'followed':
            user = event_body.get('user', {})
            if self.follow_manager:
                logger.info(f"🔔 フォロー通知受信: @{user.get('username', 'unknown')}")
                # フォロー同期を即座に実行
                await self.follow_manager.check_and_sync_followers()
        
        # その他のイベント
        else:
            logger.debug(f"未対応イベント: {event_type}")
