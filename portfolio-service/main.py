from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Portfolio Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HOLDINGS = [
    {"ticker": "AAPL", "company": "Apple Inc.", "shares": 150},
    {"ticker": "MSFT", "company": "Microsoft Corp.", "shares": 80},
    {"ticker": "GOOGL", "company": "Alphabet Inc.", "shares": 25},
    {"ticker": "AMZN", "company": "Amazon.com Inc.", "shares": 40},
    {"ticker": "TSLA", "company": "Tesla Inc.", "shares": 60},
]


@app.get("/portfolio")
def portfolio():
    return {"holdings": HOLDINGS}
