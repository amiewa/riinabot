#!/usr/bin/env python3
"""
相互フォロー判定ロジック 完全診断スクリプト v2
misskey_client.connect() の戻り値を考慮した修正版
"""
import asyncio
import sys
from database import Database
from misskey_client import MisskeyClient
from follow_manager import FollowManager

async def diagnose():
    print("=" * 60)
    print("🔍 相互フォロー判定ロジック 完全診断 v2")
    print("=" * 60)
    
    # 1. データベース接続確認
    print("\n【1/8】データベース接続確認...")
    db = Database()
    try:
        await db.connect()
        print("✅ データベース接続成功")
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Misskey API接続確認
    print("\n【2/8】Misskey API接続確認...")
    misskey = MisskeyClient()
    try:
        user_info = await misskey.connect()
        print(f"🔍 DEBUG - connect() 戻り値タイプ: {type(user_info)}")
        print(f"🔍 DEBUG - connect() 戻り値: {user_info}")
        
        if user_info is None:
            print("⚠️  connect() が None を返しました")
            print("   → misskey_client.py の connect() メソッドを確認してください")
            
            # MisskeyClientに直接アクセスしてユーザー情報取得を試行
            try:
                # i/エンドポイントで自分の情報を取得
                print("\n🔄 代替方法でユーザー情報取得を試行...")
                user_info = await misskey.client.request("i")
                print(f"✅ 代替方法成功: @{user_info.get('username', 'unknown')}")
            except Exception as alt_e:
                print(f"❌ 代替方法も失敗: {alt_e}")
                await db.close()
                return
        else:
            print(f"✅ Misskey接続成功: @{user_info.get('username', 'unknown')}")
        
        bot_user_id = user_info.get("id")
        print(f"🔍 DEBUG - Bot User ID: {bot_user_id}")
        
    except Exception as e:
        print(f"❌ Misskey接続エラー: {e}")
        import traceback
        traceback.print_exc()
        await db.close()
        return
    
    # 3. フォロワー一覧取得 (Misskey API)
    print("\n【3/8】Misskey APIからフォロワー取得...")
    try:
        followers_api = await misskey.get_followers()
        print(f"✅ Misskey APIフォロワー数: {len(followers_api)}人")
        for f in followers_api[:5]:
            print(f"   - @{f.get('username', 'unknown')} (ID: {f.get('id', 'unknown')})")
    except Exception as e:
        print(f"❌ フォロワー取得エラー: {e}")
        import traceback
        traceback.print_exc()
        followers_api = []
    
    # 4. フォロー中一覧取得 (Misskey API)
    print("\n【4/8】Misskey APIからフォロー中取得...")
    try:
        following_api = await misskey.get_following()
        print(f"✅ Misskey APIフォロー中: {len(following_api)}人")
        for f in following_api[:5]:
            print(f"   - @{f.get('username', 'unknown')} (ID: {f.get('id', 'unknown')})")
    except Exception as e:
        print(f"❌ フォロー中取得エラー: {e}")
        import traceback
        traceback.print_exc()
        following_api = []
    
    # 5. データベース内フォロワー一覧
    print("\n【5/8】データベース内フォロワー確認...")
    try:
        async with db.db.execute("SELECT user_id, username, is_following_back FROM followers") as cursor:
            db_followers = await cursor.fetchall()
        print(f"✅ データベース内フォロワー数: {len(db_followers)}人")
        for row in db_followers[:5]:
            status = "相互フォロー" if row[2] else "フォローバック未"
            print(f"   - @{row[1]} (ID: {row[0]}) - {status}")
    except Exception as e:
        print(f"❌ DB読み取りエラー: {e}")
        import traceback
        traceback.print_exc()
        db_followers = []
    
    # 6. データ不整合チェック
    print("\n【6/8】データ不整合チェック...")
    api_follower_ids = {f.get("id") for f in followers_api}
    db_follower_ids = {row[0] for row in db_followers}
    
    missing_in_db = api_follower_ids - db_follower_ids
    missing_in_api = db_follower_ids - api_follower_ids
    
    if missing_in_db:
        print(f"⚠️  Misskey APIにあるがDBにないフォロワー: {len(missing_in_db)}人")
        for fid in list(missing_in_db)[:5]:
            user = next((f for f in followers_api if f.get("id") == fid), None)
            if user:
                print(f"   - @{user.get('username', 'unknown')} (ID: {fid})")
    else:
        print("✅ APIとDBのフォロワー一致")
    
    if missing_in_api:
        print(f"⚠️  DBにあるがMisskey APIにないフォロワー: {len(missing_in_api)}人")
        for fid in list(missing_in_api)[:5]:
            user = next((row for row in db_followers if row[0] == fid), None)
            if user:
                print(f"   - @{user[1]} (ID: {fid})")
    else:
        print("✅ DBとAPIのフォロワー一致")
    
    # 7. 相互フォロー判定ロジック検証
    print("\n【7/8】相互フォロー判定ロジック検証...")
    following_ids = {f.get("id") for f in following_api}
    
    mutual_in_api = api_follower_ids & following_ids
    print(f"✅ Misskey API上の相互フォロー数: {len(mutual_in_api)}人")
    
    mutual_in_db = {row[0] for row in db_followers if row[2]}
    print(f"✅ データベース上の相互フォロー数: {len(mutual_in_db)}人")
    
    inconsistent = mutual_in_api ^ mutual_in_db  # XOR: どちらか一方にしかない
    if inconsistent:
        print(f"⚠️  相互フォロー判定の不整合: {len(inconsistent)}人")
        for fid in list(inconsistent)[:5]:
            user = next((f for f in followers_api if f.get("id") == fid), None)
            if user:
                is_mutual_api = fid in mutual_in_api
                is_mutual_db = fid in mutual_in_db
                print(f"   - @{user.get('username', 'unknown')} (API: {is_mutual_api}, DB: {is_mutual_db})")
    else:
        print("✅ API-DB間の相互フォロー判定一致")
    
    # 8. リプライ権限チェック
    print("\n【8/8】リプライ権限チェック (最近のメンション例)...")
    try:
        mentions = await misskey.get_mentions()
        if mentions:
            mention = mentions[0]
            user_id = mention.get("user", {}).get("id")
            username = mention.get("user", {}).get("username", "unknown")
            
            # データベースから相互フォロー状態確認
            async with db.db.execute(
                "SELECT is_following_back FROM followers WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                is_mutual = row[0]
                print(f"   メンション元: @{username} (ID: {user_id})")
                print(f"   DB相互フォロー: {is_mutual}")
                print(f"   API相互フォロー: {user_id in mutual_in_api}")
                if not is_mutual:
                    print(f"   ❌ リプライスキップ理由: DB上で相互フォローでない")
            else:
                print(f"   ⚠️  メンション元 @{username} はDB未登録")
                print(f"   API相互フォロー: {user_id in mutual_in_api}")
        else:
            print("   📭 最近のメンションなし")
    except Exception as e:
        print(f"   ❌ メンション取得エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 修正提案
    print("\n" + "=" * 60)
    print("💡 修正提案:")
    print("=" * 60)
    
    if missing_in_db:
        print("📌 [提案1] データベースにフォロワー情報を同期")
        print("   コマンド: docker exec riina_bot python3 /app/sync_followers.py")
    
    if inconsistent:
        print("📌 [提案2] 相互フォロー判定を再同期")
        print("   コマンド: docker compose restart")
    
    if not missing_in_db and not inconsistent:
        print("✅ すべて正常です!")
    
    print("=" * 60)
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
