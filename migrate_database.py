#!/usr/bin/env python3
import asyncio
import aiosqlite

async def migrate():
    print("🔧 データベースマイグレーション開始")
    
    db = await aiosqlite.connect("data/riina_bot.db")
    
    # 現在のカラム確認
    async with db.execute("PRAGMA table_info(followers)") as cursor:
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
    
    # is_follower カラム追加
    if "is_follower" not in column_names:
        await db.execute("ALTER TABLE followers ADD COLUMN is_follower BOOLEAN DEFAULT 1")
        await db.commit()
        print("✅ is_follower カラム追加完了")
        
        # 既存レコードを更新
        await db.execute("UPDATE followers SET is_follower = 1")
        await db.commit()
        print("✅ 既存レコード更新完了")
    else:
        print("✅ is_follower カラムは既に存在")
    
    await db.close()
    print("✅ マイグレーション完了")

if __name__ == "__main__":
    asyncio.run(migrate())
