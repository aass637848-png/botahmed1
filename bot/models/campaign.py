from datetime import datetime
from typing import List, Any
from sqlalchemy import BigInteger, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.base import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="حملة إرسال")
    content_type: Mapped[str] = mapped_column(String(32), default="text")  # text, photo, video, document
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Store list of target IDs selected for this campaign
    target_ids: Mapped[List[int]] = mapped_column(JSON, default=list)

    repeat_count: Mapped[int] = mapped_column(Integer, default=1)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=0)
    delay_between_targets: Mapped[float] = mapped_column(Float, default=1.5)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending, scheduled, running, completed, paused, failed, cancelled
    error_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="campaigns")
    logs = relationship("MessageLog", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} status={self.status} type={self.content_type}>"
