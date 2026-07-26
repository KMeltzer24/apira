import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from logging_config import RequestLoggingMiddleware, configure_logging
from models import Portfolio

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
        "Portfolio fetched",
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
