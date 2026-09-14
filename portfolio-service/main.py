import logging
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db import get_db
from logging_config import RequestLoggingMiddleware, configure_logging
from models import Portfolio, Recommendation

configure_logging()
logger = logging.getLogger("apira.portfolio")

app = FastAPI(title="Portfolio Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


class RecommendationIn(BaseModel):
    user_id: int
    body: str = Field(..., min_length=1)


@app.get("/portfolio")
def portfolio(user_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    ).scalars().all()

    holdings = [
        {"ticker": row.ticker, "company": row.company, "shares": row.shares}
        for row in rows
    ]
    tickers = [h["ticker"] for h in holdings]
    logger.info(
        "Portfolio fetched (%s holdings for user_id=%s)",
        len(holdings),
        user_id,
        extra={
            "event": "portfolio_fetched",
            "user_id": user_id,
            "holdings_count": len(holdings),
            "tickers": tickers,
            "holdings_summary": [
                {"ticker": h["ticker"], "shares": h["shares"]} for h in holdings
            ],
        },
    )
    return {"holdings": holdings}


@app.get("/recommendation")
def get_recommendation(user_id: int, db: Session = Depends(get_db)):
    row = db.get(Recommendation, user_id)
    logger.info(
        "Recommendation fetched for user_id=%s",
        user_id,
        extra={
            "event": "recommendation_fetched",
            "user_id": user_id,
            "found": row is not None,
        },
    )
    if row is None:
        return {"user_id": user_id, "body": None}
    return {"user_id": user_id, "body": row.body}


@app.put("/recommendation")
def put_recommendation(payload: RecommendationIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(Recommendation)
        .values(user_id=payload.user_id, body=payload.body, created_at=now)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"body": payload.body, "created_at": now},
        )
    )
    db.execute(stmt)
    db.commit()
    logger.info(
        "Recommendation saved for user_id=%s",
        payload.user_id,
        extra={
            "event": "recommendation_saved",
            "user_id": payload.user_id,
            "body_length": len(payload.body),
        },
    )
    return {"user_id": payload.user_id, "body": payload.body}
