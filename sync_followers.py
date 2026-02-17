#!/usr/bin/env python3
"""
フォロワー情報を Misskey API から強制同期するスクリプト
"""
import asyncio
from database import Database
from misskey_client import MisskeyClient
from follow_manager import FollowManager

async def sync():
    print("=" * 60)
    print("🔄 フォロワー強制同期")
    print("=" * 60)
    
    db = Database()
    await db.connect()
    print("✅ データベース接続完了")
    
    misskey = MisskeyClient()
    await misskey.connect()
    print("✅ Misskey API接続完了")
    
    fm = FollowManager(misskey, db)
    print("🔄 フォロワー同期開始...")
    
    await fm.check_and_sync_followers()
    print("✅ フォロワー同期完了")
    
    # 結果確認
    async with db.db.execute("SELECT COUNT(*) FROM followers") as cursor:
        row = await cursor.fetchone()
        total = row[0]
    
    async with db.db.execute(
        "SELECT COUNT(*) FROM followers WHERE is_following_back = 1"
    ) as cursor:
        row = await cursor.fetchone()
        mutual = row[0]
    
    print(f"📊 同期結果: フォロワー {total}人, 相互フォロー {mutual}人")
    
    await db.close()
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(sync())
