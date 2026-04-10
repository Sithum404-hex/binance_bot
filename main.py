"""
Crypto Trading Assistant — FastAPI Backend
============================================
Provides REST API endpoints for market analysis, AI predictions,
and real-time data via Binance public API.
"""

import os
from pathlib import Path
import httpx
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from backend.indicators import (
        calculate_rsi,
        calculate_macd,
        calculate_bollinger_bands,
        calculate_volume_profile,
        determine_trend,
        generate_signal,
        get_support_resistance,
        calculate_sma,
    )
    from backend.ai_model import (
        predict_price_linear,
        predict_price_weighted,
        calculate_prediction_confidence,
        generate_ai_explanation,
        get_market_sentiment,
    )
except ImportError:
    from indicators import (
        calculate_rsi,
        calculate_macd,
        calculate_bollinger_bands,
        calculate_volume_profile,
        determine_trend,
        generate_signal,
        get_support_resistance,
        calculate_sma,
    )
    from ai_model import (
        predict_price_linear,
        predict_price_weighted,
        calculate_prediction_confidence,
        generate_ai_explanation,
        get_market_sentiment,
    )


# ─── App Setup ────────────────────────────────────────────────
# Detect port from environment for cloud deployment
PORT = int(os.environ.get("PORT", 8000))

app = FastAPI(
    title="Crypto Trading Assistant API",
    description="AI-powered cryptocurrency analysis backend",
    version="1.0.0",
)

# CORS — allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Constants ────────────────────────────────────────────────
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
# Optional: Set BINANCE_API_KEY and BINANCE_SECRET in env for private endpoints
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")


# ─── Request / Response Models ────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., example="BTCUSDT", description="Trading pair symbol")
    budget: float = Field(100.0, ge=1, description="Available budget in USDT")


class AnalyzeResponse(BaseModel):
    symbol: str
    current_price: float
    predicted_price: float
    signal: str
    confidence: int
    rsi: float
    macd: Dict[str, float]
    trend: str
    sentiment: Dict[str, Any]
    bollinger: Dict[str, float]
    support_resistance: Dict[str, float]
    budget_allocation: Dict[str, Any]
    explanation: str
    reasons: List[str]
    prices: List[float]
    timestamps: List[int]
    volumes: List[float]


class ChatRequest(BaseModel):
    symbol: str = Field(..., example="BTCUSDT")
    question: str = Field(..., example="Should I buy BTC now?")


# ─── Helper Functions ─────────────────────────────────────────

async def fetch_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100
) -> List[List[Any]]:
    """
    Fetch candlestick (kline) data from Binance.
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
        limit: Number of candles (max 1000)
    
    Returns:
        List of kline data arrays
    """
    url = f"{BINANCE_BASE_URL}/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Binance API error: {response.status_code} — {response.text}"
            )
        
        return response.json()


async def fetch_ticker_price(symbol: str) -> float:
    """Fetch current price for a symbol."""
    url = f"{BINANCE_BASE_URL}/ticker/price"
    params = {"symbol": symbol.upper()}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch price for {symbol}"
            )
        
        data = response.json()
        return float(data["price"])


async def fetch_24h_stats(symbol: str) -> Dict[str, Any]:
    """Fetch 24-hour price statistics."""
    url = f"{BINANCE_BASE_URL}/ticker/24hr"
    params = {"symbol": symbol.upper()}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            return {}
        
        return response.json()


# ─── API Endpoints ────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Crypto Trading Assistant API",
        "version": "1.0.0"
    }


@app.get("/api/symbols")
async def get_symbols():
    """
    Get list of popular trading pairs.
    Returns curated list of high-volume USDT pairs.
    """
    symbols = [
        {"symbol": "BTCUSDT", "name": "Bitcoin", "icon": "₿"},
        {"symbol": "ETHUSDT", "name": "Ethereum", "icon": "Ξ"},
        {"symbol": "BNBUSDT", "name": "BNB", "icon": "🔶"},
        {"symbol": "SOLUSDT", "name": "Solana", "icon": "◎"},
        {"symbol": "XRPUSDT", "name": "XRP", "icon": "✕"},
        {"symbol": "ADAUSDT", "name": "Cardano", "icon": "₳"},
        {"symbol": "DOGEUSDT", "name": "Dogecoin", "icon": "🐕"},
        {"symbol": "DOTUSDT", "name": "Polkadot", "icon": "●"},
        {"symbol": "AVAXUSDT", "name": "Avalanche", "icon": "🔺"},
        {"symbol": "MATICUSDT", "name": "Polygon", "icon": "⬡"},
        {"symbol": "LINKUSDT", "name": "Chainlink", "icon": "⬡"},
        {"symbol": "LTCUSDT", "name": "Litecoin", "icon": "Ł"},
    ]
    return {"symbols": symbols}


@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    """Get current price for a symbol."""
    try:
        price = await fetch_ticker_price(symbol)
        stats = await fetch_24h_stats(symbol)
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "change_24h": float(stats.get("priceChangePercent", 0)),
            "high_24h": float(stats.get("highPrice", 0)),
            "low_24h": float(stats.get("lowPrice", 0)),
            "volume_24h": float(stats.get("volume", 0)),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Full market analysis endpoint.
    
    Fetches historical data, calculates indicators,
    generates AI predictions, and returns comprehensive analysis.
    """
    symbol = request.symbol.upper()
    budget = request.budget
    
    try:
        # Fetch historical candlestick data (100 hourly candles)
        klines = await fetch_klines(symbol, interval="1h", limit=100)
        
        if not klines:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Extract price and volume data
        closes = [float(k[4]) for k in klines]      # Close prices
        volumes = [float(k[5]) for k in klines]      # Volumes
        timestamps = [int(k[0]) for k in klines]     # Open timestamps
        highs = [float(k[2]) for k in klines]        # High prices
        lows = [float(k[3]) for k in klines]         # Low prices
        opens = [float(k[1]) for k in klines]        # Open prices
        
        current_price = closes[-1]
        
        # ─── Calculate Indicators ─────────────────────
        rsi = calculate_rsi(closes)
        macd = calculate_macd(closes)
        bollinger = calculate_bollinger_bands(closes)
        volume_info = calculate_volume_profile(volumes)
        trend = determine_trend(closes)
        support_resistance = get_support_resistance(closes)
        
        # ─── Generate Signal ──────────────────────────
        signal_data = generate_signal(rsi, macd, trend, closes)
        
        # ─── AI Price Prediction ──────────────────────
        predicted_price = predict_price_weighted(closes)
        pred_confidence = calculate_prediction_confidence(closes, predicted_price)
        
        # Blend signal confidence with prediction confidence
        final_confidence = int(0.6 * signal_data["confidence"] + 0.4 * pred_confidence)
        
        # ─── Market Sentiment ─────────────────────────
        stats = await fetch_24h_stats(symbol)
        price_change_24h = float(stats.get("priceChangePercent", 0))
        sentiment = get_market_sentiment(rsi, trend, macd["histogram"], price_change_24h)
        
        # ─── Budget Allocation ────────────────────────
        coins_possible = budget / current_price if current_price > 0 else 0
        budget_allocation = {
            "budget": budget,
            "coins_possible": round(coins_possible, 8),
            "entry_price": current_price,
            "suggested_stop_loss": round(current_price * 0.95, 2),
            "suggested_take_profit": round(current_price * 1.08, 2),
        }
        
        # ─── AI Explanation ───────────────────────────
        explanation = await generate_ai_explanation(
            symbol=symbol,
            price=current_price,
            rsi=rsi,
            trend=trend,
            signal=signal_data["signal"],
            confidence=final_confidence,
            macd=macd,
            predicted_price=predicted_price,
        )
        
        return AnalyzeResponse(
            symbol=symbol,
            current_price=current_price,
            predicted_price=predicted_price,
            signal=signal_data["signal"],
            confidence=final_confidence,
            rsi=rsi,
            macd=macd,
            trend=trend,
            sentiment=sentiment,
            bollinger=bollinger,
            support_resistance=support_resistance,
            budget_allocation=budget_allocation,
            explanation=explanation,
            reasons=signal_data["reasons"],
            prices=closes,
            timestamps=timestamps,
            volumes=volumes,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    AI Chat endpoint for free-form questions about a symbol.
    """
    symbol = request.symbol.upper()
    
    try:
        # Get current market data
        price = await fetch_ticker_price(symbol)
        klines = await fetch_klines(symbol, interval="1h", limit=50)
        closes = [float(k[4]) for k in klines]
        
        rsi = calculate_rsi(closes)
        macd = calculate_macd(closes)
        trend = determine_trend(closes)
        signal_data = generate_signal(rsi, macd, trend, closes)
        predicted = predict_price_weighted(closes)
        
        explanation = await generate_ai_explanation(
            symbol=symbol,
            price=price,
            rsi=rsi,
            trend=trend,
            signal=signal_data["signal"],
            confidence=signal_data["confidence"],
            macd=macd,
            predicted_price=predicted,
        )
        
        return {
            "response": explanation,
            "signal": signal_data["signal"],
            "price": price,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/api/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query("1h", pattern="^(1m|5m|15m|30m|1h|4h|1d|1w)$"),
    limit: int = Query(100, ge=10, le=500),
):
    """
    Get raw kline/candlestick data for charting.
    
    Returns OHLCV data formatted for Chart.js.
    """
    try:
        klines = await fetch_klines(symbol.upper(), interval, limit)
        
        formatted = []
        for k in klines:
            formatted.append({
                "time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        
        return {"symbol": symbol.upper(), "interval": interval, "data": formatted}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Static File Serving (Frontend) ───────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    # Serve static assets (CSS, JS, images)
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    @app.get("/")
    async def serve_index():
        """Serve the frontend index page."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    
    @app.get("/app")
    @app.get("/app/{rest_of_path:path}")
    async def serve_frontend(rest_of_path: str = ""):
        """Serve the frontend HTML application."""
        file_path = FRONTEND_DIR / rest_of_path
        if rest_of_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        """Fallback root when frontend is not found."""
        return {
            "status": "running",
            "service": "Crypto Trading Assistant API",
            "version": "1.0.0",
            "frontend": "not found"
        }


# ─── Run with: uvicorn main:app --reload --port 8000 ──────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
