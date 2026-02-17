#!/usr/bin/env python3
import asyncio
from database import Database
from misskey_client import MisskeyClient

async def diagnose():
    print("=" * 60)
    print("🔍 相互フォロー判定ロジック 診断")
    print("=" * 60)
    
    db = Database()
    await db.connect()
    print("✅ データベース接続成功")
    
    misskey = MisskeyClient()
    user_info = await misskey.connect()
    print(f"✅ Misskey接続成功: @{user_info.get('username')}")
    
    # フォロワー取得
    print("\n【Misskey APIフォロワー】")
    followers_api = await misskey.get_followers()
    print(f"フォロワー数: {len(followers_api)}人")
    for f in followers_api[:5]:
        print(f"  - @{f.get('username')} (ID: {f.get('id')})")
    
    # フォロー中取得
    print("\n【Misskey APIフォロー中】")
    following_api = await misskey.get_following()
    print(f"フォロー中: {len(following_api)}人")
    for f in following_api[:5]:
        print(f"  - @{f.get('username')} (ID: {f.get('id')})")
    
    # データベース確認
    print("\n【データベース内フォロワー】")
    async with db.db.execute("SELECT user_id, username, is_follower, is_following_back FROM followers") as cursor:
        db_followers = await cursor.fetchall()
    print(f"DB登録数: {len(db_followers)}人")
    for row in db_followers:
        status = "相互" if row[2] and row[3] else "片方向"
        print(f"  - @{row[1]} (ID: {row[0]}) - {status} (follower:{row[2]}, following:{row[3]})")
    
    # 不整合チェック
    print("\n【不整合チェック】")
    api_follower_ids = {f.get("id") for f in followers_api}
    db_follower_ids = {row[0] for row in db_followers}
    
    missing = api_follower_ids - db_follower_ids
    if missing:
        print(f"⚠️  APIにあるがDBにない: {len(missing)}人")
        for fid in missing:
            user = next((f for f in followers_api if f.get("id") == fid), None)
            if user:
                print(f"  - @{user.get('username')} (ID: {fid})")
    else:
        print("✅ APIとDB一致")
    
    # 相互フォロー判定
    print("\n【相互フォロー判定】")
    following_ids = {f.get("id") for f in following_api}
    mutual_in_api = api_follower_ids & following_ids
    print(f"API上の相互フォロー: {len(mutual_in_api)}人")
    
    mutual_in_db = {row[0] for row in db_followers if row[2] and row[3]}
    print(f"DB上の相互フォロー: {len(mutual_in_db)}人")
    
    print("\n💡 修正方法:")
    if missing:
        print("  docker exec riina_bot python3 /app/sync_followers.py")
    else:
        print("  ✅ 問題なし")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
