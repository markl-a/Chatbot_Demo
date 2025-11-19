"""
資料庫模型定義

定義對話歷史、用戶和會話的資料庫模型。
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """用戶模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)

    # 用戶資訊
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # 偏好設定
    preferences = Column(JSON, default={})

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # 關聯
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Session(Base):
    """會話模型"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)

    # 用戶關聯
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 會話資訊
    title = Column(String(200), nullable=True)
    model_name = Column(String(100), nullable=True)

    # 統計資訊
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 設定
    settings = Column(JSON, default={})

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # 關聯
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, session_id='{self.session_id}')>"


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    # 會話關聯
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # 消息內容
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # RAG 資訊
    used_rag = Column(Boolean, default=False)
    retrieved_docs = Column(JSON, nullable=True)

    # 生成資訊
    model_name = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)

    # 安全資訊
    is_safe = Column(Boolean, default=True)
    is_emergency = Column(Boolean, default=False)
    safety_flags = Column(JSON, nullable=True)

    # 評分和反饋
    rating = Column(Integer, nullable=True)  # 1-5 星
    feedback = Column(Text, nullable=True)

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', session_id={self.session_id})>"


class KnowledgeDocument(Base):
    """知識文檔模型（用於 RAG）"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)

    # 文檔資訊
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    source = Column(String(500), nullable=True)

    # 分類
    category = Column(String(50), nullable=True)
    tags = Column(JSON, default=[])

    # 嵌入資訊
    embedding_model = Column(String(100), nullable=True)
    vector_id = Column(String(100), nullable=True)  # FAISS 向量 ID

    # 元數據
    metadata = Column(JSON, default={})

    # 狀態
    is_active = Column(Boolean, default=True)

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<KnowledgeDocument(id={self.id}, title='{self.title}')>"


class APIKey(Base):
    """API 金鑰模型"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    # 用戶關聯
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 金鑰資訊
    key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)

    # 權限
    permissions = Column(JSON, default=[])

    # 使用限制
    rate_limit = Column(Integer, default=100)  # 每小時請求數
    daily_limit = Column(Integer, default=1000)  # 每日請求數

    # 統計
    total_requests = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)

    # 狀態
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    user = relationship("User")

    def __repr__(self):
        return f"<APIKey(id={self.id}, user_id={self.user_id}, name='{self.name}')>"


class Feedback(Base):
    """用戶反饋模型"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)

    # 用戶和會話關聯
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    # 反饋內容
    rating = Column(Integer, nullable=False)  # 1-5
    category = Column(String(50), nullable=True)  # helpful, accurate, safe, etc.
    comment = Column(Text, nullable=True)

    # 元數據
    metadata = Column(JSON, default={})

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    user = relationship("User")
    session = relationship("Session")
    message = relationship("Message")

    def __repr__(self):
        return f"<Feedback(id={self.id}, rating={self.rating})>"
