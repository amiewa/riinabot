#!/usr/bin/env python3
import asyncio
from database import Database
from misskey_client import MisskeyClient

async def sync():
    print("=" * 60)
    print("🔄 フォロワー強制同期 v2")
    print("=" * 60)
    
    db = Database()
    await db.connect()
    print("✅ データベース接続完了")
    
    misskey = MisskeyClient()
    await misskey.connect()
    print("✅ Misskey API接続完了")
    
    # フォロワー一覧取得
    print("\n🔄 フォロワー同期開始...")
    followers = await misskey.get_followers()
    follower_ids = {f.get("id") for f in followers}
    print(f"  Misskey APIフォロワー: {len(followers)}人")
    
    # フォロー中一覧取得
    following = await misskey.get_following()
    following_ids = {f.get("id") for f in following}
    print(f"  Misskey APIフォロー中: {len(following)}人")
    
    # 相互フォローID
    mutual_ids = follower_ids & following_ids
    print(f"  相互フォロー: {len(mutual_ids)}人")
    
    # データベース同期
    print("\n📝 データベース更新中...")
    
    # 既存フォロワーを取得
    db_followers = await db.get_all_followers()
    db_follower_ids = {f["user_id"] for f in db_followers}
    
    # 新規フォロワーを追加
    new_follower_ids = follower_ids - db_follower_ids
    for fid in new_follower_ids:
        user = next((f for f in followers if f.get("id") == fid), None)
        if user:
            username = user.get("username", "unknown")
            await db.add_follower(fid, username)
            print(f"  ➕ 新規追加: @{username}")
    
    # フォロー解除されたユーザーを削除
    unfollowed_ids = db_follower_ids - follower_ids
    for fid in unfollowed_ids:
        await db.remove_follower(fid)
        print(f"  ➖ 削除: {fid}")
    
    # 全フォロワーの相互フォロー状態を更新
    print("\n🔄 相互フォロー状態を更新中...")
    for fid in follower_ids:
        is_mutual = fid in mutual_ids
        await db.set_following_back(fid, is_mutual)
        user = next((f for f in followers if f.get("id") == fid), None)
        if user:
            username = user.get("username", "unknown")
            status = "✅ 相互" if is_mutual else "⏸️  片方向"
            print(f"  {status}: @{username}")
    
    # 結果確認
    print("\n📊 同期結果:")
    async with db.db.execute("SELECT COUNT(*) FROM followers") as cursor:
        row = await cursor.fetchone()
        total = row[0]
    
    async with db.db.execute(
        "SELECT COUNT(*) FROM followers WHERE is_following_back = 1"
    ) as cursor:
        row = await cursor.fetchone()
        mutual = row[0]
    
    print(f"  フォロワー総数: {total}人")
    print(f"  相互フォロー: {mutual}人")
    
    await db.close()
    print("\n" + "=" * 60)
    print("✅ 同期完了")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(sync())
