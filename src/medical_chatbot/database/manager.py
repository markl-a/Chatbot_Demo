"""
資料庫管理器

提供資料庫連接、會話管理和常用操作。
"""
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
import hashlib
import secrets

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session as DBSession
from sqlalchemy.pool import QueuePool
from loguru import logger

from .models import Base, User, Session, Message, KnowledgeDocument, APIKey, Feedback
from ..utils.exceptions import DatabaseException, ConnectionException, QueryException


class DatabaseManager:
    """資料庫管理器"""

    def __init__(
        self,
        database_url: str = "sqlite:///./medical_chatbot.db",
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        初始化資料庫管理器

        Args:
            database_url: 資料庫連接字串
            echo: 是否輸出 SQL 語句
            pool_size: 連接池大小
            max_overflow: 最大溢出連接數
        """
        self.database_url = database_url
        self.echo = echo

        try:
            # 創建引擎
            if database_url.startswith("sqlite"):
                # SQLite 不支援連接池
                self.engine = create_engine(
                    database_url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                )
            else:
                # PostgreSQL/MySQL 使用連接池
                self.engine = create_engine(
                    database_url,
                    echo=echo,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_pre_ping=True,  # 連接前檢查
                )

            # 創建會話工廠
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            logger.info(f"資料庫管理器初始化成功: {database_url}")

        except Exception as e:
            logger.error(f"資料庫管理器初始化失敗: {e}")
            raise ConnectionException(f"無法連接到資料庫: {str(e)}")

    def create_tables(self):
        """創建所有資料表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("資料表創建成功")
        except Exception as e:
            logger.error(f"創建資料表失敗: {e}")
            raise DatabaseException(f"創建資料表失敗: {str(e)}")

    def drop_tables(self):
        """刪除所有資料表"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("所有資料表已刪除")
        except Exception as e:
            logger.error(f"刪除資料表失敗: {e}")
            raise DatabaseException(f"刪除資料表失敗: {str(e)}")

    @contextmanager
    def get_db(self):
        """獲取資料庫會話（上下文管理器）"""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"資料庫操作失敗: {e}")
            raise
        finally:
            db.close()

    # ========================================================================
    # 用戶管理
    # ========================================================================

    def create_user(
        self, username: str, email: Optional[str] = None, password: Optional[str] = None, **kwargs
    ) -> User:
        """創建用戶"""
        with self.get_db() as db:
            # 檢查用戶是否存在
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                raise DatabaseException(f"用戶已存在: {username}")

            # 密碼雜湊
            hashed_password = None
            if password:
                hashed_password = self._hash_password(password)

            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                **kwargs,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(f"創建用戶: {username}")
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        """獲取用戶"""
        with self.get_db() as db:
            return db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根據用戶名獲取用戶"""
        with self.get_db() as db:
            return db.query(User).filter(User.username == username).first()

    def update_user_login(self, user_id: int):
        """更新用戶最後登入時間"""
        with self.get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                db.commit()

    # ========================================================================
    # 會話管理
    # ========================================================================

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ) -> Session:
        """創建會話"""
        with self.get_db() as db:
            if not session_id:
                session_id = self._generate_session_id()

            session = Session(
                session_id=session_id,
                user_id=user_id,
                model_name=model_name,
                **kwargs,
            )

            db.add(session)
            db.commit()
            db.refresh(session)

            logger.info(f"創建會話: {session_id}")
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """獲取會話"""
        with self.get_db() as db:
            return db.query(Session).filter(Session.session_id == session_id).first()

    def get_user_sessions(
        self, user_id: int, limit: int = 10
    ) -> List[Session]:
        """獲取用戶的會話列表"""
        with self.get_db() as db:
            return (
                db.query(Session)
                .filter(Session.user_id == user_id)
                .order_by(Session.created_at.desc())
                .limit(limit)
                .all()
            )

    def end_session(self, session_id: str):
        """結束會話"""
        with self.get_db() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                session.ended_at = datetime.utcnow()
                db.commit()
                logger.info(f"結束會話: {session_id}")

    # ========================================================================
    # 消息管理
    # ========================================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        **kwargs,
    ) -> Message:
        """添加消息"""
        with self.get_db() as db:
            # 獲取會話
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if not session:
                raise DatabaseException(f"會話不存在: {session_id}")

            # 創建消息
            message = Message(
                session_id=session.id,
                role=role,
                content=content,
                **kwargs,
            )

            db.add(message)

            # 更新會話統計
            session.message_count += 1
            session.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(message)

            return message

    def get_session_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """獲取會話的所有消息"""
        with self.get_db() as db:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if not session:
                return []

            query = (
                db.query(Message)
                .filter(Message.session_id == session.id)
                .order_by(Message.created_at.asc())
            )

            if limit:
                query = query.limit(limit)

            return query.all()

    def get_conversation_history(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        """獲取對話歷史（格式化為對話格式）"""
        messages = self.get_session_messages(session_id, limit=limit)

        history = []
        for msg in messages:
            history.append({"role": msg.role, "content": msg.content})

        return history

    # ========================================================================
    # 知識文檔管理
    # ========================================================================

    def add_knowledge_document(
        self, content: str, title: Optional[str] = None, **kwargs
    ) -> KnowledgeDocument:
        """添加知識文檔"""
        with self.get_db() as db:
            doc = KnowledgeDocument(title=title, content=content, **kwargs)

            db.add(doc)
            db.commit()
            db.refresh(doc)

            logger.info(f"添加知識文檔: {title or doc.id}")
            return doc

    def get_knowledge_documents(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        limit: int = 100,
    ) -> List[KnowledgeDocument]:
        """獲取知識文檔"""
        with self.get_db() as db:
            query = db.query(KnowledgeDocument)

            if category:
                query = query.filter(KnowledgeDocument.category == category)

            if is_active is not None:
                query = query.filter(KnowledgeDocument.is_active == is_active)

            return query.order_by(KnowledgeDocument.created_at.desc()).limit(limit).all()

    # ========================================================================
    # API 金鑰管理
    # ========================================================================

    def create_api_key(
        self, user_id: int, name: Optional[str] = None, **kwargs
    ) -> APIKey:
        """創建 API 金鑰"""
        with self.get_db() as db:
            key = self._generate_api_key()

            api_key = APIKey(user_id=user_id, key=key, name=name, **kwargs)

            db.add(api_key)
            db.commit()
            db.refresh(api_key)

            logger.info(f"創建 API 金鑰: {name or api_key.id}")
            return api_key

    def verify_api_key(self, key: str) -> Optional[APIKey]:
        """驗證 API 金鑰"""
        with self.get_db() as db:
            api_key = (
                db.query(APIKey)
                .filter(and_(APIKey.key == key, APIKey.is_active == True))
                .first()
            )

            if api_key:
                # 更新使用記錄
                api_key.total_requests += 1
                api_key.last_used = datetime.utcnow()
                db.commit()

            return api_key

    # ========================================================================
    # 反饋管理
    # ========================================================================

    def add_feedback(
        self,
        rating: int,
        user_id: Optional[int] = None,
        message_id: Optional[int] = None,
        **kwargs,
    ) -> Feedback:
        """添加反饋"""
        with self.get_db() as db:
            feedback = Feedback(
                user_id=user_id, message_id=message_id, rating=rating, **kwargs
            )

            db.add(feedback)
            db.commit()
            db.refresh(feedback)

            return feedback

    def get_average_rating(self, days: int = 7) -> float:
        """獲取平均評分"""
        from datetime import timedelta

        with self.get_db() as db:
            since = datetime.utcnow() - timedelta(days=days)

            result = (
                db.query(Feedback)
                .filter(Feedback.created_at >= since)
                .all()
            )

            if not result:
                return 0.0

            return sum(f.rating for f in result) / len(result)

    # ========================================================================
    # 統計和分析
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        with self.get_db() as db:
            stats = {
                "total_users": db.query(User).count(),
                "total_sessions": db.query(Session).count(),
                "total_messages": db.query(Message).count(),
                "total_documents": db.query(KnowledgeDocument).count(),
                "average_rating": self.get_average_rating(),
            }

            return stats

    # ========================================================================
    # 工具方法
    # ========================================================================

    @staticmethod
    def _hash_password(password: str) -> str:
        """密碼雜湊"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _generate_session_id() -> str:
        """生成會話 ID"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _generate_api_key() -> str:
        """生成 API 金鑰"""
        return f"sk-{secrets.token_urlsafe(48)}"
