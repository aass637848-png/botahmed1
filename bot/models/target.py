from sqlalchemy import BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.base import Base, TimestampMixin


class Target(Base, TimestampMixin):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    chat_type: Mapped[str] = mapped_column(String(32), default="channel")
    can_post_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    can_send_media: Mapped[bool] = mapped_column(Boolean, default=True)
    status_description: Mapped[str] = mapped_column(String(255), default="صالح للإرسال")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    owner = relationship("User", back_populates="targets")
    logs = relationship("MessageLog", back_populates="target", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Target chat_id={self.chat_id} title={self.title} type={self.chat_type}>"
