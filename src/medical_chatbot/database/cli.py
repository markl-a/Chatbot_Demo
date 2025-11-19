"""
資料庫 CLI 工具

用於資料庫初始化、遷移和管理。
"""
import typer
from pathlib import Path
from loguru import logger

app = typer.Typer(help="資料庫管理工具")


@app.command()
def init(
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    )
):
    """初始化資料庫（創建所有表）"""
    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        db_manager.create_tables()

        typer.echo("✓ 資料庫初始化成功！")
        typer.echo(f"  資料庫: {database_url}")

    except Exception as e:
        typer.echo(f"✗ 資料庫初始化失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def drop(
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="強制刪除（不確認）"
    ),
):
    """刪除所有資料表"""
    if not force:
        confirm = typer.confirm("⚠️  確定要刪除所有資料表嗎？此操作不可恢復！")
        if not confirm:
            typer.echo("操作已取消")
            raise typer.Exit()

    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        db_manager.drop_tables()

        typer.echo("✓ 所有資料表已刪除")

    except Exception as e:
        typer.echo(f"✗ 刪除資料表失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def reset(
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="強制重置（不確認）"
    ),
):
    """重置資料庫（刪除並重新創建所有表）"""
    if not force:
        confirm = typer.confirm("⚠️  確定要重置資料庫嗎？所有資料將被刪除！")
        if not confirm:
            typer.echo("操作已取消")
            raise typer.Exit()

    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        db_manager.drop_tables()
        db_manager.create_tables()

        typer.echo("✓ 資料庫已重置")

    except Exception as e:
        typer.echo(f"✗ 資料庫重置失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def stats(
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    )
):
    """顯示資料庫統計資訊"""
    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        statistics = db_manager.get_statistics()

        typer.echo("\n📊 資料庫統計資訊:\n")
        typer.echo(f"  總用戶數:     {statistics['total_users']}")
        typer.echo(f"  總會話數:     {statistics['total_sessions']}")
        typer.echo(f"  總消息數:     {statistics['total_messages']}")
        typer.echo(f"  總文檔數:     {statistics['total_documents']}")
        typer.echo(f"  平均評分:     {statistics['average_rating']:.2f}/5.0")
        typer.echo()

    except Exception as e:
        typer.echo(f"✗ 獲取統計資訊失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def create_user(
    username: str = typer.Argument(..., help="用戶名"),
    email: str = typer.Option(None, "--email", "-e", help="電子郵件"),
    password: str = typer.Option(None, "--password", "-p", help="密碼"),
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    ),
):
    """創建新用戶"""
    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        user = db_manager.create_user(username=username, email=email, password=password)

        typer.echo(f"✓ 創建用戶成功！")
        typer.echo(f"  用戶 ID:  {user.id}")
        typer.echo(f"  用戶名:   {user.username}")
        typer.echo(f"  郵箱:     {user.email or '未設置'}")

    except Exception as e:
        typer.echo(f"✗ 創建用戶失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def create_api_key(
    user_id: int = typer.Argument(..., help="用戶 ID"),
    name: str = typer.Option(None, "--name", "-n", help="API 金鑰名稱"),
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    ),
):
    """為用戶創建 API 金鑰"""
    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)
        api_key = db_manager.create_api_key(user_id=user_id, name=name)

        typer.echo(f"✓ 創建 API 金鑰成功！")
        typer.echo(f"  金鑰 ID:   {api_key.id}")
        typer.echo(f"  用戶 ID:   {api_key.user_id}")
        typer.echo(f"  名稱:      {api_key.name or '未命名'}")
        typer.echo(f"  金鑰:      {api_key.key}")
        typer.echo()
        typer.echo("  ⚠️  請妥善保管此金鑰，不會再次顯示！")

    except Exception as e:
        typer.echo(f"✗ 創建 API 金鑰失敗: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def seed(
    database_url: str = typer.Option(
        "sqlite:///./medical_chatbot.db",
        "--url",
        "-u",
        help="資料庫連接字串",
    )
):
    """填充測試資料"""
    from .manager import DatabaseManager

    try:
        db_manager = DatabaseManager(database_url=database_url)

        # 創建測試用戶
        user = db_manager.create_user(
            username="test_user",
            email="test@example.com",
            password="test123",
            full_name="測試用戶",
        )

        # 創建測試會話
        session = db_manager.create_session(
            user_id=user.id, model_name="test-model", title="測試會話"
        )

        # 添加測試消息
        db_manager.add_message(
            session_id=session.session_id,
            role="user",
            content="你好，這是測試消息",
        )

        db_manager.add_message(
            session_id=session.session_id,
            role="assistant",
            content="你好！我是醫療聊天機器人，很高興為您服務。",
        )

        # 添加測試知識文檔
        db_manager.add_knowledge_document(
            title="高血壓介紹",
            content="高血壓是指血壓持續高於正常值的疾病...",
            category="心血管",
        )

        typer.echo("✓ 測試資料填充成功！")
        typer.echo(f"  創建用戶:     {user.username}")
        typer.echo(f"  創建會話:     {session.session_id}")
        typer.echo(f"  創建消息:     2 條")
        typer.echo(f"  創建文檔:     1 個")

    except Exception as e:
        typer.echo(f"✗ 填充測試資料失敗: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
