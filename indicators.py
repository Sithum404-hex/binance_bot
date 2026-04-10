"""
Technical Analysis Indicators Module
=====================================
Calculates RSI, MACD, Moving Averages, and other technical indicators
for cryptocurrency market analysis.
"""

from typing import List, Dict, Any, Optional


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average (SMA).
    
    Args:
        prices: List of closing prices
        period: Number of periods for the moving average
    
    Returns:
        List of SMA values (NaN for insufficient data points)
    """
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(float('nan'))
        else:
            window = prices[i - period + 1:i + 1]
            sma.append(sum(window) / period)
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        prices: List of closing prices
        period: Number of periods for the EMA
    
    Returns:
        List of EMA values
    """
    multiplier = 2 / (period + 1)
    ema = [prices[0]]  # Start with first price
    
    for i in range(1, len(prices)):
        value = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(value)
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI).
    
    RSI measures the speed and magnitude of recent price changes
    to evaluate overbought or oversold conditions.
    
    Args:
        prices: List of closing prices (needs at least period+1 values)
        period: RSI period (default: 14)
    
    Returns:
        RSI value between 0 and 100
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data
    
    # Calculate price changes
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    # Separate gains and losses
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # Calculate average gain/loss using Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Apply smoothing for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    # Calculate RSI
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: List of closing prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
    
    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' values
    """
    if len(prices) < slow_period:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    
    # Calculate fast and slow EMAs
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    # MACD line = Fast EMA - Slow EMA
    macd_line = [fast_ema[i] - slow_ema[i] for i in range(len(prices))]
    
    # Signal line = EMA of MACD line
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Histogram = MACD - Signal
    histogram = macd_line[-1] - signal_line[-1]
    
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram, 4)
    }


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Dict[str, float]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of closing prices
        period: SMA period (default: 20)
        std_dev: Number of standard deviations (default: 2.0)
    
    Returns:
        Dictionary with 'upper', 'middle', 'lower' band values
    """
    if len(prices) < period:
        current = prices[-1]
        return {"upper": current, "middle": current, "lower": current}
    
    recent = prices[-period:]
    middle = sum(recent) / period
    
    # Standard deviation
    variance = sum((p - middle) ** 2 for p in recent) / period
    std = variance ** 0.5
    
    return {
        "upper": round(middle + std_dev * std, 2),
        "middle": round(middle, 2),
        "lower": round(middle - std_dev * std, 2)
    }


def calculate_volume_profile(volumes: List[float], period: int = 20) -> Dict[str, Any]:
    """
    Analyze volume trends.
    
    Args:
        volumes: List of trading volumes
        period: Period for average volume calculation
    
    Returns:
        Dictionary with volume analysis
    """
    if not volumes:
        return {"avg_volume": 0, "current_volume": 0, "volume_trend": "neutral"}
    
    recent = volumes[-period:] if len(volumes) >= period else volumes
    avg_volume = sum(recent) / len(recent)
    current_volume = volumes[-1]
    
    if current_volume > avg_volume * 1.5:
        volume_trend = "high"
    elif current_volume < avg_volume * 0.5:
        volume_trend = "low"
    else:
        volume_trend = "normal"
    
    return {
        "avg_volume": round(avg_volume, 2),
        "current_volume": round(current_volume, 2),
        "volume_trend": volume_trend
    }


def determine_trend(prices: List[float], short_period: int = 7, long_period: int = 25) -> str:
    """
    Determine the current market trend using moving average crossover.
    
    Args:
        prices: List of closing prices
        short_period: Short MA period
        long_period: Long MA period
    
    Returns:
        'uptrend', 'downtrend', or 'sideways'
    """
    if len(prices) < long_period:
        return "sideways"
    
    short_ma = sum(prices[-short_period:]) / short_period
    long_ma = sum(prices[-long_period:]) / long_period
    
    # Calculate percentage difference
    diff_pct = ((short_ma - long_ma) / long_ma) * 100
    
    if diff_pct > 0.5:
        return "uptrend"
    elif diff_pct < -0.5:
        return "downtrend"
    else:
        return "sideways"


def generate_signal(
    rsi: float,
    macd: Dict[str, float],
    trend: str,
    prices: List[float]
) -> Dict[str, Any]:
    """
    Generate a trading signal based on technical indicators.
    
    Combines RSI, MACD, and trend analysis to produce
    a weighted BUY/SELL/HOLD signal with confidence.
    
    Args:
        rsi: RSI value
        macd: MACD dictionary
        trend: Current trend string
        prices: Recent prices
    
    Returns:
        Dictionary with 'signal', 'confidence', and 'reasons'
    """
    score = 0  # Positive = bullish, Negative = bearish
    reasons = []
    
    # --- RSI Analysis (weight: 30%) ---
    if rsi < 30:
        score += 3
        reasons.append(f"RSI is oversold at {rsi:.1f} — potential bounce")
    elif rsi < 40:
        score += 1.5
        reasons.append(f"RSI approaching oversold at {rsi:.1f}")
    elif rsi > 70:
        score -= 3
        reasons.append(f"RSI is overbought at {rsi:.1f} — potential pullback")
    elif rsi > 60:
        score -= 1.5
        reasons.append(f"RSI approaching overbought at {rsi:.1f}")
    else:
        reasons.append(f"RSI is neutral at {rsi:.1f}")
    
    # --- MACD Analysis (weight: 35%) ---
    if macd["histogram"] > 0 and macd["macd"] > macd["signal"]:
        score += 3.5
        reasons.append("MACD shows bullish crossover with positive momentum")
    elif macd["histogram"] < 0 and macd["macd"] < macd["signal"]:
        score -= 3.5
        reasons.append("MACD shows bearish crossover with negative momentum")
    elif macd["histogram"] > 0:
        score += 1
        reasons.append("MACD histogram is positive but weakening")
    else:
        score -= 1
        reasons.append("MACD histogram is negative but stabilizing")
    
    # --- Trend Analysis (weight: 35%) ---
    if trend == "uptrend":
        score += 3.5
        reasons.append("Price is in an uptrend (short MA > long MA)")
    elif trend == "downtrend":
        score -= 3.5
        reasons.append("Price is in a downtrend (short MA < long MA)")
    else:
        reasons.append("Price is moving sideways — consolidation phase")
    
    # --- Price momentum check ---
    if len(prices) >= 5:
        recent_change = ((prices[-1] - prices[-5]) / prices[-5]) * 100
        if recent_change > 2:
            score += 1
            reasons.append(f"Recent momentum is positive ({recent_change:.1f}%)")
        elif recent_change < -2:
            score -= 1
            reasons.append(f"Recent momentum is negative ({recent_change:.1f}%)")
    
    # --- Generate final signal ---
    max_score = 11  # Maximum possible absolute score
    confidence = min(int(abs(score) / max_score * 100), 95)
    confidence = max(confidence, 15)  # Minimum 15% confidence
    
    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"
        confidence = max(confidence, 40)  # HOLD needs reasonable confidence
    
    return {
        "signal": signal,
        "confidence": confidence,
        "score": round(score, 2),
        "reasons": reasons
    }


def get_support_resistance(prices: List[float], lookback: int = 50) -> Dict[str, float]:
    """
    Calculate approximate support and resistance levels.
    
    Args:
        prices: List of closing prices
        lookback: Number of periods to analyze
    
    Returns:
        Dictionary with 'support' and 'resistance' levels
    """
    recent = prices[-lookback:] if len(prices) >= lookback else prices
    
    return {
        "support": round(min(recent), 2),
        "resistance": round(max(recent), 2)
    }
