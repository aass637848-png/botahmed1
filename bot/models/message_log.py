from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.base import Base


class MessageLog(Base):
    __tablename__ = "messages_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("targets.id", ondelete="SET NULL"), nullable=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    target_title: Mapped[str] = mapped_column(String(255), default="")
    iteration: Mapped[int] = mapped_column(Integer, default=1)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # success, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="logs")
    target = relationship("Target", back_populates="logs")

    def __repr__(self) -> str:
        return f"<MessageLog id={self.id} campaign={self.campaign_id} status={self.status}>"
