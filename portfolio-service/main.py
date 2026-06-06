from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Portfolio

app = FastAPI(title="Portfolio Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/portfolio")
def portfolio(user_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    ).scalars().all()

    holdings = [
        {"ticker": row.ticker, "company": row.company, "shares": row.shares}
        for row in rows
    ]
    return {"holdings": holdings}
