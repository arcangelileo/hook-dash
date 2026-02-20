import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    response_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    response_body: Mapped[str] = mapped_column(String(10000), default='{"ok": true}', nullable=False)
    response_content_type: Mapped[str] = mapped_column(
        String(100), default="application/json", nullable=False
    )
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="endpoints")
    webhook_requests = relationship(
        "WebhookRequest", back_populates="endpoint", cascade="all, delete-orphan"
    )
    forwarding_config = relationship(
        "ForwardingConfig", back_populates="endpoint", uselist=False, cascade="all, delete-orphan"
    )
