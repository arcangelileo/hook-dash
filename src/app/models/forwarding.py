import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ForwardingConfig(Base):
    __tablename__ = "forwarding_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    endpoint_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    endpoint = relationship("Endpoint", back_populates="forwarding_config")
    logs = relationship("ForwardingLog", back_populates="forwarding_config", cascade="all, delete-orphan")


class ForwardingLog(Base):
    __tablename__ = "forwarding_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    forwarding_config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("forwarding_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    webhook_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("webhook_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    forwarding_config = relationship("ForwardingConfig", back_populates="logs")
    webhook_request = relationship("WebhookRequest", back_populates="forwarding_logs")
