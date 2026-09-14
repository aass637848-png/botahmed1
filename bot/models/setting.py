from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from bot.database.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Setting key={self.key} user={self.user_id} value={self.value}>"
