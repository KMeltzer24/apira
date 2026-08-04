import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from logging_config import RequestLoggingMiddleware, configure_logging
from models import User

configure_logging()
logger = logging.getLogger("apira.user")

app = FastAPI(title="User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.username == body.username)
    ).scalar_one_or_none()

    if user is None or user.password != body.password:
        logger.warning(
            "Login failed (invalid credentials)",
            extra={"event": "login_failed", "error_code": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.info(
        "Login succeeded (user_id=%s)",
        user.id,
        extra={"event": "login_succeeded", "user_id": user.id},
    )
    return {"success": True, "username": user.username, "user_id": user.id}
