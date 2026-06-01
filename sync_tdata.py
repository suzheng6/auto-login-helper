"""独立子进程：将 Telethon session 转换为 AyuGram tdata。
由主程序 subprocess 调用，避免 opentele monkey-patch 污染主进程。
"""
import sys
import asyncio
import os


def main():
    if len(sys.argv) < 5:
        print("ERR:参数不足", flush=True)
        sys.exit(1)

    session_path = sys.argv[1]
    tdata_dir = sys.argv[2]
    api_id = int(sys.argv[3])
    api_hash = sys.argv[4]
    phone = sys.argv[5] if len(sys.argv) > 5 else ""
    pass2fa = sys.argv[6] if len(sys.argv) > 6 else ""

    from opentele.tl import TelegramClient as OTeleClient
    from opentele.td import TDesktop, Account
    from opentele.api import API, CreateNewSession

    # opentele 默认硬编码单实例最多 3 个账号；AyuGram 支持更多，
    # 这里运行时放开上限（加账号检查与读取 tdata 都动态读取此类属性）。
    TDesktop.kMaxAccounts = 100

    async def sync():
        if phone:
            api = API.TelegramDesktop.Generate(system="windows", unique_id=phone)
        else:
            api = API.TelegramDesktop

        client = OTeleClient(session=session_path, api=api)
        await client.connect()

        if not await client.is_user_authorized():
            print("ERR:会话未授权", flush=True)
            return

        os.makedirs(tdata_dir, exist_ok=True)

        # 尝试加载现有 tdata：AyuGram 已有账号则追加，空目录/读不到则新建
        tdesk = None
        # 注意：opentele 的 OpenTeleException 继承自 BaseException 而非 Exception，
        # 必须用 except BaseException 才能捕获（空目录/读不到账号时会抛出）。
        try:
            loaded = TDesktop(tdata_dir, api=API.TelegramDesktop)
            if loaded.isLoaded():
                tdesk = loaded
        except BaseException:
            tdesk = None

        if tdesk is not None:
            existing_ids = {acc.UserId for acc in tdesk.accounts}
            me = await client.get_me()
            if me.id in existing_ids:
                print("OK:SKIP already exists", flush=True)
                await client.disconnect()
                return
            await Account.FromTelethon(
                client, flag=CreateNewSession, owner=tdesk, api=api,
                password=pass2fa or None,
            )
        else:
            tdesk = await TDesktop.FromTelethon(
                client, flag=CreateNewSession, api=api,
                password=pass2fa or None,
            )

        tdesk.SaveTData(tdata_dir)
        print("OK", flush=True)
        await client.disconnect()

    asyncio.run(sync())


if __name__ == "__main__":
    main()
