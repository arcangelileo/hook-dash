import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WebhookRequest(Base):
    __tablename__ = "webhook_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    endpoint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    headers: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    query_params: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON
    content_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    body_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    endpoint = relationship("Endpoint", back_populates="webhook_requests")
    forwarding_logs = relationship(
        "ForwardingLog", back_populates="webhook_request", cascade="all, delete-orphan"
    )
