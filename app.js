/**
 * ═══════════════════════════════════════════════════════════════
 * CryptoAI — Frontend Application
 * ═══════════════════════════════════════════════════════════════
 * Handles UI interactions, API communication, chart rendering,
 * and real-time data updates.
 */

// ─── Configuration ──────────────────────────────────────────────
const CONFIG = {
    backendUrl: localStorage.getItem('backendUrl') || 'http://localhost:8000',
    refreshInterval: parseInt(localStorage.getItem('refreshInterval')) || 30,
    defaultBudget: parseInt(localStorage.getItem('defaultBudget')) || 100,
    chartStyle: localStorage.getItem('chartStyle') || 'line',
};

// ─── State ──────────────────────────────────────────────────────
const state = {
    currentPage: 'dashboard',
    selectedSymbol: 'BTCUSDT',
    budget: CONFIG.defaultBudget,
    interval: '1h',
    analysisData: null,
    priceChart: null,
    macdChart: null,
    autoRefreshTimer: null,
    isAnalyzing: false,
    backendOnline: false,
};

// ─── DOM References ─────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Initialization ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Initialize Lucide icons
    if (window.lucide) lucide.createIcons();

    // Setup event listeners
    setupNavigation();
    setupControls();
    setupChat();
    setupSettings();

    // Start clock
    updateClock();
    setInterval(updateClock, 1000);

    // Check backend status
    await checkBackendStatus();

    // Hide loading overlay after short delay
    setTimeout(() => {
        const overlay = $('#loadingOverlay');
        if (overlay) overlay.classList.add('hidden');
    }, 1200);

    // Load settings
    loadSettings();

    // Auto-refresh price
    startAutoRefresh();
}

// ═══════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════

function setupNavigation() {
    $$('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            navigateTo(page);
        });
    });

    // Mobile menu toggle
    const menuToggle = $('#menuToggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            $('#sidebar').classList.toggle('open');
        });
    }

    // Close sidebar on page click (mobile)
    $('.main-content').addEventListener('click', () => {
        $('#sidebar').classList.remove('open');
    });
}

function navigateTo(page) {
    state.currentPage = page;

    // Update nav items
    $$('.nav-item').forEach(nav => nav.classList.remove('active'));
    $(`.nav-item[data-page="${page}"]`).classList.add('active');

    // Update pages
    $$('.page').forEach(p => p.classList.remove('active'));
    $(`#page${capitalize(page)}`).classList.add('active');

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        market: 'Market Overview',
        assistant: 'AI Assistant',
        settings: 'Settings'
    };
    $('#pageTitle').textContent = titles[page] || 'Dashboard';

    // Load page-specific data
    if (page === 'market') loadMarketData();

    // Re-initialize icons
    if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════════════════
// CONTROLS & ANALYSIS
// ═══════════════════════════════════════════════════════════════

function setupControls() {
    // Coin selector
    $('#coinSelect').addEventListener('change', (e) => {
        state.selectedSymbol = e.target.value;
    });

    // Budget input
    const budgetInput = $('#budgetInput');
    budgetInput.value = CONFIG.defaultBudget;
    budgetInput.addEventListener('change', (e) => {
        state.budget = parseFloat(e.target.value) || 100;
    });

    // Interval selector
    $('#intervalSelect').addEventListener('change', (e) => {
        state.interval = e.target.value;
    });

    // Analyze button
    $('#analyzeBtn').addEventListener('click', () => runAnalysis());

    // Chart type buttons
    $$('.chart-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            $$('.chart-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (state.analysisData) {
                renderPriceChart(state.analysisData, btn.dataset.type);
            }
        });
    });
}

async function runAnalysis() {
    if (state.isAnalyzing) return;

    const analyzeBtn = $('#analyzeBtn');
    state.isAnalyzing = true;
    analyzeBtn.classList.add('loading');
    analyzeBtn.disabled = true;

    try {
        const response = await fetch(`${CONFIG.backendUrl}/api/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: state.selectedSymbol,
                budget: state.budget,
            }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        state.analysisData = data;
        updateDashboard(data);
        showToast('Analysis complete', 'success');

    } catch (error) {
        console.error('Analysis failed:', error);
        showToast(`Analysis failed: ${error.message}`, 'error');
    } finally {
        state.isAnalyzing = false;
        analyzeBtn.classList.remove('loading');
        analyzeBtn.disabled = false;
    }
}

// ═══════════════════════════════════════════════════════════════
// DASHBOARD UPDATE
// ═══════════════════════════════════════════════════════════════

function updateDashboard(data) {
    // ─── Price Card ───────────────────────────────────
    const priceEl = $('#currentPrice');
    animateValue(priceEl, formatPrice(data.current_price));

    const changeEl = $('#priceChange');
    const change24h = data.sentiment?.price_change_24h || 0;
    changeEl.textContent = `${change24h >= 0 ? '+' : ''}${change24h.toFixed(2)}%`;
    changeEl.className = `stat-change ${change24h >= 0 ? 'positive' : 'negative'}`;

    // ─── Signal Card ──────────────────────────────────
    const signalBadge = $('#signalBadge');
    signalBadge.textContent = data.signal;
    signalBadge.className = `stat-value signal-badge ${data.signal.toLowerCase()}`;

    const confEl = $('#signalConfidence');
    confEl.textContent = `${data.confidence}% confidence`;
    confEl.className = `stat-change ${data.signal === 'BUY' ? 'positive' : data.signal === 'SELL' ? 'negative' : 'neutral'}`;

    // ─── RSI Card ─────────────────────────────────────
    $('#rsiValue').textContent = data.rsi.toFixed(1);
    const rsiStatus = $('#rsiStatus');
    if (data.rsi < 30) {
        rsiStatus.textContent = 'Oversold';
        rsiStatus.className = 'stat-change positive';
    } else if (data.rsi > 70) {
        rsiStatus.textContent = 'Overbought';
        rsiStatus.className = 'stat-change negative';
    } else {
        rsiStatus.textContent = 'Neutral';
        rsiStatus.className = 'stat-change neutral';
    }

    // ─── Trend Card ───────────────────────────────────
    const trendVal = $('#trendValue');
    trendVal.textContent = capitalize(data.trend);

    const sentimentText = $('#sentimentText');
    sentimentText.textContent = data.sentiment?.sentiment || 'Neutral';
    const sentClass = (data.sentiment?.sentiment || '').toLowerCase().includes('bull') ? 'positive'
        : (data.sentiment?.sentiment || '').toLowerCase().includes('bear') ? 'negative' : 'neutral';
    sentimentText.className = `stat-change ${sentClass}`;

    // ─── Confidence Meter ─────────────────────────────
    updateConfidenceMeter(data.confidence, data.signal);

    // ─── Budget Info ──────────────────────────────────
    if (data.budget_allocation) {
        const ba = data.budget_allocation;
        $('#coinsPossible').textContent = formatNumber(ba.coins_possible, 6);
        $('#stopLoss').textContent = formatPrice(ba.suggested_stop_loss);
        $('#takeProfit').textContent = formatPrice(ba.suggested_take_profit);
    }
    $('#predictedPrice').textContent = formatPrice(data.predicted_price);

    // ─── AI Explanation ───────────────────────────────
    updateAIPanel(data.explanation);

    // ─── Chart ────────────────────────────────────────
    const activeChartType = $('.chart-type-btn.active')?.dataset.type || 'line';
    renderPriceChart(data, activeChartType);
    renderMACDChart(data);

    // ─── Chart title ──────────────────────────────────
    const pair = data.symbol.replace('USDT', '/USDT');
    $('#chartTitle').textContent = `${pair} Price Chart`;

    // ─── Reasons Panel ────────────────────────────────
    if (data.reasons && data.reasons.length > 0) {
        const reasonsPanel = $('#reasonsPanel');
        reasonsPanel.style.display = 'block';
        const list = $('#reasonsList');
        list.innerHTML = '';
        data.reasons.forEach(reason => {
            const li = document.createElement('li');
            const iconClass = reason.toLowerCase().includes('bull') || reason.toLowerCase().includes('oversold') || reason.toLowerCase().includes('positive')
                ? 'bullish'
                : reason.toLowerCase().includes('bear') || reason.toLowerCase().includes('overbought') || reason.toLowerCase().includes('negative')
                    ? 'bearish' : 'neutral';
            li.innerHTML = `<span class="reason-icon ${iconClass}"></span>${reason}`;
            list.appendChild(li);
        });
    }
}

function updateConfidenceMeter(confidence, signal) {
    const ring = $('#confidenceRing');
    const circumference = 2 * Math.PI * 50; // r=50
    const offset = circumference - (confidence / 100) * circumference;
    ring.style.strokeDasharray = circumference;
    ring.style.strokeDashoffset = offset;

    // Color based on signal
    if (signal === 'BUY') ring.style.stroke = 'var(--green)';
    else if (signal === 'SELL') ring.style.stroke = 'var(--red)';
    else ring.style.stroke = 'var(--text-tertiary)';

    $('#confidenceValue').textContent = `${confidence}%`;
    
    const label = confidence >= 70 ? 'High confidence' : confidence >= 40 ? 'Moderate confidence' : 'Low confidence';
    $('#confidenceLabel').textContent = label;
}

function updateAIPanel(explanation) {
    const chat = $('#aiChat');
    // Clear welcome message
    const welcome = chat.querySelector('.welcome');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = 'ai-message';
    messageDiv.innerHTML = `
        <div class="ai-avatar"><i data-lucide="bot"></i></div>
        <div class="ai-bubble">${formatExplanation(explanation)}</div>
    `;
    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;

    if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════════════════
// CHARTS
// ═══════════════════════════════════════════════════════════════

function renderPriceChart(data, type = 'line') {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;

    // Destroy existing chart
    if (state.priceChart) {
        state.priceChart.destroy();
        state.priceChart = null;
    }

    const labels = data.timestamps.map(t => new Date(t));
    const prices = data.prices;

    // Calculate SMA for overlay
    const sma20 = [];
    for (let i = 0; i < prices.length; i++) {
        if (i < 19) { sma20.push(null); continue; }
        const sum = prices.slice(i - 19, i + 1).reduce((a, b) => a + b, 0);
        sma20.push(sum / 20);
    }

    const datasets = [];

    if (type === 'line') {
        // Price line
        datasets.push({
            label: 'Price',
            data: prices,
            borderColor: '#60a5fa',
            backgroundColor: createGradient(ctx, '#60a5fa'),
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHitRadius: 10,
        });

        // SMA overlay
        datasets.push({
            label: 'SMA 20',
            data: sma20,
            borderColor: 'rgba(251, 191, 36, 0.6)',
            borderWidth: 1.5,
            borderDash: [5, 3],
            fill: false,
            tension: 0.3,
            pointRadius: 0,
        });
    } else {
        // Volume bars
        datasets.push({
            label: 'Volume',
            data: data.volumes,
            backgroundColor: data.prices.map((p, i) =>
                i > 0 && p >= data.prices[i - 1]
                    ? 'rgba(74, 222, 128, 0.5)'
                    : 'rgba(248, 113, 113, 0.5)'
            ),
            borderRadius: 3,
        });
    }

    state.priceChart = new Chart(ctx, {
        type: type === 'line' ? 'line' : 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: type === 'line',
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 11 },
                        boxWidth: 12,
                        boxHeight: 2,
                        padding: 16,
                        usePointStyle: false,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 29, 36, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { family: 'Inter', weight: '600' },
                    bodyFont: { family: 'Inter' },
                    callbacks: {
                        label: (ctx) => {
                            if (type === 'line') return `${ctx.dataset.label}: $${formatNumber(ctx.parsed.y)}`;
                            return `Volume: ${formatNumber(ctx.parsed.y)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        displayFormats: { hour: 'HH:mm', day: 'MMM d' }
                    },
                    grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
                    ticks: { color: '#64748b', font: { family: 'Inter', size: 10 }, maxTicksLimit: 10 },
                    border: { display: false }
                },
                y: {
                    position: 'right',
                    grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
                    ticks: {
                        color: '#64748b',
                        font: { family: 'Inter', size: 10 },
                        callback: (v) => type === 'line' ? '$' + formatNumber(v) : formatNumber(v),
                    },
                    border: { display: false }
                }
            }
        }
    });
}

function renderMACDChart(data) {
    const ctx = document.getElementById('macdChart');
    if (!ctx) return;

    if (state.macdChart) {
        state.macdChart.destroy();
        state.macdChart = null;
    }

    // Compute MACD values for all data points (simplified)
    const prices = data.prices;
    const macdValues = [];
    const signalValues = [];
    const histogramValues = [];

    // Compute EMAs
    const ema12 = computeEMA(prices, 12);
    const ema26 = computeEMA(prices, 26);

    const macdLine = prices.map((_, i) => ema12[i] - ema26[i]);
    const signalLine = computeEMA(macdLine, 9);

    for (let i = 0; i < prices.length; i++) {
        macdValues.push(macdLine[i]);
        signalValues.push(signalLine[i]);
        histogramValues.push(macdLine[i] - signalLine[i]);
    }

    const labels = data.timestamps.map(t => new Date(t));

    state.macdChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Histogram',
                    data: histogramValues,
                    backgroundColor: histogramValues.map(v => v >= 0 ? 'rgba(74,222,128,0.4)' : 'rgba(248,113,113,0.4)'),
                    borderRadius: 2,
                    order: 2,
                },
                {
                    label: 'MACD',
                    data: macdValues,
                    type: 'line',
                    borderColor: '#60a5fa',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false,
                    order: 1,
                },
                {
                    label: 'Signal',
                    data: signalValues,
                    type: 'line',
                    borderColor: '#fbbf24',
                    borderWidth: 1.5,
                    borderDash: [3, 2],
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false,
                    order: 1,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 10 },
                        boxWidth: 10,
                        boxHeight: 2,
                        padding: 10,
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(26,29,36,0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 10,
                }
            },
            scales: {
                x: {
                    type: 'time',
                    display: false,
                    border: { display: false }
                },
                y: {
                    position: 'right',
                    grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
                    ticks: { color: '#64748b', font: { family: 'Inter', size: 9 }, maxTicksLimit: 4 },
                    border: { display: false }
                }
            }
        }
    });
}

function computeEMA(data, period) {
    const k = 2 / (period + 1);
    const ema = [data[0]];
    for (let i = 1; i < data.length; i++) {
        ema.push(data[i] * k + ema[i - 1] * (1 - k));
    }
    return ema;
}

function createGradient(canvas, color) {
    const ctx = canvas.getContext ? canvas.getContext('2d') : canvas.ctx;
    if (!ctx || !ctx.createLinearGradient) {
        // Chart.js canvas element — use chart area when available
        return `${color}15`;
    }
    const gradient = ctx.createLinearGradient(0, 0, 0, 350);
    gradient.addColorStop(0, `${color}30`);
    gradient.addColorStop(1, `${color}02`);
    return gradient;
}

// ═══════════════════════════════════════════════════════════════
// MARKET PAGE
// ═══════════════════════════════════════════════════════════════

async function loadMarketData() {
    const grid = $('#marketGrid');
    grid.innerHTML = `<div class="market-loading"><div class="spinner"></div><p>Loading market data...</p></div>`;

    try {
        // Fetch symbols list
        const symbolsRes = await fetch(`${CONFIG.backendUrl}/api/symbols`);
        if (!symbolsRes.ok) throw new Error('Failed to fetch symbols');
        const { symbols } = await symbolsRes.json();

        // Fetch prices for each symbol
        const pricePromises = symbols.map(async (sym) => {
            try {
                const res = await fetch(`${CONFIG.backendUrl}/api/price/${sym.symbol}`);
                if (!res.ok) return { ...sym, price: 0, change_24h: 0, volume_24h: 0, high_24h: 0, low_24h: 0 };
                const data = await res.json();
                return { ...sym, ...data };
            } catch {
                return { ...sym, price: 0, change_24h: 0, volume_24h: 0, high_24h: 0, low_24h: 0 };
            }
        });

        const marketData = await Promise.all(pricePromises);

        grid.innerHTML = '';
        marketData.forEach(coin => {
            const changeClass = coin.change_24h >= 0 ? 'positive' : 'negative';
            const changeSign = coin.change_24h >= 0 ? '+' : '';

            const card = document.createElement('div');
            card.className = 'market-card';
            card.innerHTML = `
                <div class="market-card-header">
                    <div class="market-coin">
                        <div class="market-coin-icon">${coin.icon}</div>
                        <div>
                            <div class="market-coin-name">${coin.name}</div>
                            <div class="market-coin-symbol">${coin.symbol}</div>
                        </div>
                    </div>
                    <div class="market-change ${changeClass}">${changeSign}${coin.change_24h.toFixed(2)}%</div>
                </div>
                <div class="market-price">$${formatNumber(coin.price)}</div>
                <div class="market-stats">
                    <span>H: $${formatNumber(coin.high_24h)}</span>
                    <span>L: $${formatNumber(coin.low_24h)}</span>
                    <span>Vol: ${formatVolume(coin.volume_24h)}</span>
                </div>
            `;

            // Click to analyze
            card.addEventListener('click', () => {
                state.selectedSymbol = coin.symbol;
                $('#coinSelect').value = coin.symbol;
                navigateTo('dashboard');
                runAnalysis();
            });

            grid.appendChild(card);
        });

    } catch (error) {
        grid.innerHTML = `
            <div class="market-loading">
                <p style="color: var(--red);">Failed to load market data. Is the backend running?</p>
                <button class="btn btn-ghost" onclick="loadMarketData()" style="margin-top:10px;">
                    <span>Retry</span>
                </button>
            </div>
        `;
    }

    if (window.lucide) lucide.createIcons();

    // Refresh button
    const refreshBtn = $('#refreshMarket');
    if (refreshBtn) {
        refreshBtn.onclick = () => loadMarketData();
    }
}

// ═══════════════════════════════════════════════════════════════
// AI CHAT PAGE
// ═══════════════════════════════════════════════════════════════

function setupChat() {
    const input = $('#chatInput');
    const sendBtn = $('#chatSendBtn');

    sendBtn.addEventListener('click', () => sendChatMessage());
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

async function sendChatMessage() {
    const input = $('#chatInput');
    const message = input.value.trim();
    if (!message) return;

    const symbol = $('#chatCoinSelect').value;
    const messagesContainer = $('#chatMessages');

    // Add user message
    const userMsg = document.createElement('div');
    userMsg.className = 'user-message';
    userMsg.innerHTML = `<div class="user-bubble">${escapeHTML(message)}</div>`;
    messagesContainer.appendChild(userMsg);

    input.value = '';

    // Add loading indicator
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'ai-message';
    loadingMsg.id = 'chatLoading';
    loadingMsg.innerHTML = `
        <div class="ai-avatar"><i data-lucide="bot"></i></div>
        <div class="ai-bubble"><div class="spinner" style="width:20px;height:20px;border-width:2px;"></div></div>
    `;
    messagesContainer.appendChild(loadingMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    if (window.lucide) lucide.createIcons();

    try {
        const response = await fetch(`${CONFIG.backendUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, question: message }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        // Remove loading
        loadingMsg.remove();

        // Add AI response
        const aiMsg = document.createElement('div');
        aiMsg.className = 'ai-message';
        aiMsg.innerHTML = `
            <div class="ai-avatar"><i data-lucide="bot"></i></div>
            <div class="ai-bubble">
                ${formatExplanation(data.response)}
                <div style="margin-top:8px;font-size:0.75rem;color:var(--text-muted);">
                    Signal: <strong style="color:${data.signal === 'BUY' ? 'var(--green)' : data.signal === 'SELL' ? 'var(--red)' : 'var(--text-secondary)'};">${data.signal}</strong>
                    · Price: $${formatNumber(data.price)}
                </div>
            </div>
        `;
        messagesContainer.appendChild(aiMsg);

    } catch (error) {
        loadingMsg.remove();
        const errMsg = document.createElement('div');
        errMsg.className = 'ai-message';
        errMsg.innerHTML = `
            <div class="ai-avatar"><i data-lucide="bot"></i></div>
            <div class="ai-bubble" style="border-left:3px solid var(--red);">
                <p>Sorry, I couldn't process your request. ${error.message}</p>
            </div>
        `;
        messagesContainer.appendChild(errMsg);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    if (window.lucide) lucide.createIcons();
}

// ═══════════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════════

function setupSettings() {
    $('#saveSettings').addEventListener('click', saveSettings);
}

function loadSettings() {
    $('#backendUrl').value = CONFIG.backendUrl;
    $('#refreshInterval').value = CONFIG.refreshInterval;
    $('#defaultBudget').value = CONFIG.defaultBudget;
    $('#chartStyle').value = CONFIG.chartStyle;
    $('#budgetInput').value = CONFIG.defaultBudget;
    state.budget = CONFIG.defaultBudget;
}

function saveSettings() {
    const backendUrl = $('#backendUrl').value.trim().replace(/\/$/, '');
    const refreshInterval = parseInt($('#refreshInterval').value) || 30;
    const defaultBudget = parseInt($('#defaultBudget').value) || 100;
    const chartStyle = $('#chartStyle').value;

    localStorage.setItem('backendUrl', backendUrl);
    localStorage.setItem('refreshInterval', String(refreshInterval));
    localStorage.setItem('defaultBudget', String(defaultBudget));
    localStorage.setItem('chartStyle', chartStyle);

    CONFIG.backendUrl = backendUrl;
    CONFIG.refreshInterval = refreshInterval;
    CONFIG.defaultBudget = defaultBudget;
    CONFIG.chartStyle = chartStyle;

    // Update dashboard budget
    $('#budgetInput').value = defaultBudget;
    state.budget = defaultBudget;

    // Restart auto-refresh
    startAutoRefresh();

    // Re-check backend
    checkBackendStatus();

    showToast('Settings saved successfully', 'success');
}

// ═══════════════════════════════════════════════════════════════
// BACKEND STATUS
// ═══════════════════════════════════════════════════════════════

async function checkBackendStatus() {
    try {
        const res = await fetch(`${CONFIG.backendUrl}/`, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
            state.backendOnline = true;
            const status = $('#serverStatus');
            status.innerHTML = '<span class="status-dot online"></span><span class="status-text">Backend Online</span>';
        } else {
            throw new Error();
        }
    } catch {
        state.backendOnline = false;
        const status = $('#serverStatus');
        status.innerHTML = '<span class="status-dot offline"></span><span class="status-text">Backend Offline</span>';
    }
}

// ═══════════════════════════════════════════════════════════════
// AUTO REFRESH
// ═══════════════════════════════════════════════════════════════

function startAutoRefresh() {
    if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);

    state.autoRefreshTimer = setInterval(async () => {
        // Only refresh if on dashboard and not currently analyzing
        if (state.currentPage === 'dashboard' && state.analysisData && !state.isAnalyzing) {
            try {
                const res = await fetch(`${CONFIG.backendUrl}/api/price/${state.selectedSymbol}`);
                if (res.ok) {
                    const data = await res.json();
                    const priceEl = $('#currentPrice');
                    animateValue(priceEl, formatPrice(data.price));

                    const changeEl = $('#priceChange');
                    changeEl.textContent = `${data.change_24h >= 0 ? '+' : ''}${data.change_24h.toFixed(2)}%`;
                    changeEl.className = `stat-change ${data.change_24h >= 0 ? 'positive' : 'negative'}`;
                }
            } catch { /* silent fail for auto-refresh */ }
        }

        // Periodic backend check
        checkBackendStatus();
    }, CONFIG.refreshInterval * 1000);
}

// ═══════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════

function formatPrice(price) {
    if (!price || price === 0) return '$0.00';
    if (price >= 1) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    // Small prices (< $1)
    return `$${price.toFixed(6)}`;
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return '—';
    if (typeof num === 'string') num = parseFloat(num);
    if (Math.abs(num) >= 1) return num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    return num.toFixed(Math.max(decimals, 4));
}

function formatVolume(vol) {
    if (!vol) return '0';
    if (vol >= 1e9) return (vol / 1e9).toFixed(1) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
    return vol.toFixed(0);
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatExplanation(text) {
    if (!text) return '<p>No analysis available.</p>';
    // Convert markdown-like bold
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert newlines to paragraphs
    html = html.split('\n').filter(l => l.trim()).map(l => `<p>${l}</p>`).join('');
    return html;
}

function animateValue(element, newValue) {
    element.style.opacity = '0.5';
    element.style.transform = 'translateY(-2px)';
    setTimeout(() => {
        element.textContent = newValue;
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
        element.style.transition = 'all 0.3s ease';
    }, 150);
}

function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const clockEl = $('#clock');
    if (clockEl) clockEl.textContent = `${hours}:${minutes}:${seconds}`;
}

function showToast(message, type = 'info') {
    const container = $('#toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span> ${escapeHTML(message)}`;
    
    container.appendChild(toast);

    // Auto-remove
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
