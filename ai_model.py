"""
AI Model Module
================
Handles AI-powered price predictions and natural language explanations
using both simple regression and OpenAI API integration.
"""

import os
import json
import math
from typing import List, Dict, Any, Optional

# OpenAI integration (optional — works without it)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ─── Configuration ───────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def predict_price_linear(prices: List[float], periods_ahead: int = 1) -> float:
    """
    Predict future price using simple linear regression.
    
    Uses ordinary least squares to fit a line to recent prices
    and extrapolate forward.
    
    Args:
        prices: Historical closing prices
        periods_ahead: Number of periods to predict ahead
    
    Returns:
        Predicted price value
    """
    if len(prices) < 2:
        return prices[-1] if prices else 0.0
    
    # Use last 30 data points for regression
    data = prices[-30:] if len(prices) > 30 else prices
    n = len(data)
    
    # X values: 0, 1, 2, ..., n-1
    x_values = list(range(n))
    y_values = data
    
    # Calculate means
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    
    # Calculate slope (m) and intercept (b)
    numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
    denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return prices[-1]
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Predict
    predicted = slope * (n - 1 + periods_ahead) + intercept
    
    # Sanity check: don't predict more than ±15% from current price
    current_price = prices[-1]
    max_change = current_price * 0.15
    predicted = max(current_price - max_change, min(current_price + max_change, predicted))
    
    return round(predicted, 2)


def predict_price_weighted(prices: List[float]) -> float:
    """
    Predict price using weighted moving average approach.
    
    Gives more weight to recent prices and combines with
    linear regression for a blended prediction.
    
    Args:
        prices: Historical closing prices
    
    Returns:
        Predicted price value
    """
    if len(prices) < 3:
        return prices[-1] if prices else 0.0
    
    # Weighted average of last 10 prices (recent prices get more weight)
    window = prices[-10:] if len(prices) >= 10 else prices
    weights = list(range(1, len(window) + 1))
    total_weight = sum(weights)
    
    wma = sum(window[i] * weights[i] for i in range(len(window))) / total_weight
    
    # Blend with linear regression
    linear_pred = predict_price_linear(prices)
    
    # 60% weighted average, 40% linear regression
    blended = 0.6 * wma + 0.4 * linear_pred
    
    return round(blended, 2)


def calculate_prediction_confidence(prices: List[float], predicted: float) -> int:
    """
    Estimate confidence level for a price prediction.
    
    Based on recent price volatility — lower volatility = higher confidence.
    
    Args:
        prices: Historical prices
        predicted: Predicted price value
    
    Returns:
        Confidence percentage (0-100)
    """
    if len(prices) < 10:
        return 30
    
    recent = prices[-20:] if len(prices) >= 20 else prices
    
    # Calculate coefficient of variation (volatility measure)
    mean_price = sum(recent) / len(recent)
    if mean_price == 0:
        return 30
    
    variance = sum((p - mean_price) ** 2 for p in recent) / len(recent)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_price
    
    # Lower CV = higher confidence
    # CV of 0.01 (1%) → ~85% confidence
    # CV of 0.05 (5%) → ~45% confidence
    # CV of 0.10 (10%) → ~25% confidence
    confidence = max(15, min(90, int(100 - cv * 800)))
    
    return confidence


async def generate_ai_explanation(
    symbol: str,
    price: float,
    rsi: float,
    trend: str,
    signal: str,
    confidence: int,
    macd: Dict[str, float],
    predicted_price: float
) -> str:
    """
    Generate a natural language explanation of the market analysis.
    
    Uses OpenAI API if available, otherwise falls back to
    template-based explanations.
    
    Args:
        symbol: Trading pair symbol
        price: Current price
        rsi: RSI value
        trend: Market trend
        signal: Trading signal
        confidence: Confidence percentage
        macd: MACD values
        predicted_price: Predicted price
    
    Returns:
        Human-readable explanation string
    """
    # Try OpenAI first
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        try:
            return await _openai_explanation(
                symbol, price, rsi, trend, signal, confidence, macd, predicted_price
            )
        except Exception as e:
            print(f"OpenAI API error: {e}. Falling back to template.")
    
    # Fallback: Template-based explanation
    return _template_explanation(
        symbol, price, rsi, trend, signal, confidence, macd, predicted_price
    )


async def _openai_explanation(
    symbol: str,
    price: float,
    rsi: float,
    trend: str,
    signal: str,
    confidence: int,
    macd: Dict[str, float],
    predicted_price: float
) -> str:
    """Generate explanation using OpenAI API."""
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""You are a professional crypto trading analyst. Analyze the following data and give a concise 2-3 sentence market explanation.

Symbol: {symbol}
Current Price: ${price:,.2f}
RSI: {rsi}
Trend: {trend}
MACD: {macd['macd']:.4f} (Signal: {macd['signal']:.4f})
Signal: {signal}
Confidence: {confidence}%
Predicted Price: ${predicted_price:,.2f}

Be specific, mention the indicators, and explain why the {signal} signal makes sense. Keep it professional and concise."""

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()


def _template_explanation(
    symbol: str,
    price: float,
    rsi: float,
    trend: str,
    signal: str,
    confidence: int,
    macd: Dict[str, float],
    predicted_price: float
) -> str:
    """Generate explanation using templates (no API needed)."""
    
    pair = symbol.replace("USDT", "/USDT")
    price_direction = "higher" if predicted_price > price else "lower"
    price_diff_pct = abs((predicted_price - price) / price * 100)
    
    # RSI context
    if rsi < 30:
        rsi_text = f"The RSI at {rsi:.1f} indicates the asset is heavily oversold, suggesting a potential price recovery."
    elif rsi < 40:
        rsi_text = f"The RSI at {rsi:.1f} is approaching oversold territory, hinting at a possible upward reversal."
    elif rsi > 70:
        rsi_text = f"The RSI at {rsi:.1f} signals overbought conditions — a pullback may be on the horizon."
    elif rsi > 60:
        rsi_text = f"The RSI at {rsi:.1f} is trending toward overbought levels, warranting caution."
    else:
        rsi_text = f"The RSI at {rsi:.1f} sits in neutral territory, showing balanced momentum."
    
    # Trend context
    trend_map = {
        "uptrend": "bullish momentum with short-term moving averages above long-term levels",
        "downtrend": "bearish pressure with short-term moving averages below long-term levels",
        "sideways": "consolidation, with price moving within a narrow range"
    }
    trend_text = trend_map.get(trend, "uncertain market conditions")
    
    # MACD context
    if macd["histogram"] > 0:
        macd_text = "MACD confirms positive momentum with a bullish histogram."
    else:
        macd_text = "MACD shows weakening momentum with a bearish histogram reading."
    
    # Signal-specific commentary
    if signal == "BUY":
        signal_intro = f"📈 **{pair}** is showing a buying opportunity at ${price:,.2f}."
        signal_outro = f"With {confidence}% confidence, our model predicts the price could move {price_direction} to approximately ${predicted_price:,.2f} ({price_diff_pct:.1f}% change). Consider accumulating within your risk tolerance."
    elif signal == "SELL":
        signal_intro = f"📉 **{pair}** is signaling caution at ${price:,.2f}."
        signal_outro = f"With {confidence}% confidence, the prediction points {price_direction} toward ${predicted_price:,.2f} ({price_diff_pct:.1f}% change). Consider securing profits or setting stop-losses."
    else:
        signal_intro = f"⏸️ **{pair}** is in a wait-and-see zone at ${price:,.2f}."
        signal_outro = f"The price may move {price_direction} toward ${predicted_price:,.2f}. Hold current positions and monitor for a clearer signal before acting."
    
    explanation = f"""{signal_intro}

The market currently shows {trend_text}. {rsi_text} {macd_text}

{signal_outro}"""
    
    return explanation.strip()


def get_market_sentiment(
    rsi: float,
    trend: str,
    macd_histogram: float,
    price_change_24h: Optional[float] = None
) -> Dict[str, Any]:
    """
    Determine overall market sentiment.
    
    Args:
        rsi: RSI value
        trend: Trend direction
        macd_histogram: MACD histogram value
        price_change_24h: 24h price change percentage (optional)
    
    Returns:
        Dictionary with sentiment label and score
    """
    score = 0
    
    # RSI sentiment
    if rsi < 35:
        score += 2  # Oversold = potential bullish
    elif rsi > 65:
        score -= 2  # Overbought = potential bearish
    
    # Trend sentiment
    if trend == "uptrend":
        score += 2
    elif trend == "downtrend":
        score -= 2
    
    # MACD sentiment
    if macd_histogram > 0:
        score += 1
    else:
        score -= 1
    
    # 24h change sentiment
    if price_change_24h is not None:
        if price_change_24h > 3:
            score += 1
        elif price_change_24h < -3:
            score -= 1
    
    # Determine label
    if score >= 3:
        sentiment = "Strongly Bullish"
    elif score >= 1:
        sentiment = "Bullish"
    elif score <= -3:
        sentiment = "Strongly Bearish"
    elif score <= -1:
        sentiment = "Bearish"
    else:
        sentiment = "Neutral"
    
    return {
        "sentiment": sentiment,
        "score": score,
        "max_score": 6
    }
