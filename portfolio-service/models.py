from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    ticker: Mapped[str]
    company: Mapped[str]
    shares: Mapped[int]


class Recommendation(Base):
    __tablename__ = "recommendations"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
