const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(value);
};

const renderHoldings = (holdings) => {
    const grid = document.getElementById('holdings-grid');
    grid.innerHTML = ''; // Clear loading state

    if (!holdings || holdings.length === 0) {
        grid.innerHTML = '<div class="loading-state"><p>No active positions found.</p></div>';
        return;
    }

    let totalVal = 0;
    let totalInvested = 0;
    let totalDayPnl = 0;

    holdings.forEach(item => {
        const value = item.quantity * item.last_price;
        const invested = item.quantity * item.average_price;
        const pnl = value - invested;
        
        // Calculate Day P&L using previous close price
        const dayPnl = (item.last_price - item.close_price) * item.quantity;
        
        const pnlPercent = (pnl / invested) * 100;

        totalVal += value;
        totalInvested += invested;
        totalDayPnl += dayPnl;

        const isProfit = pnl >= 0;
        const pnlClass = isProfit ? 'profit-text' : 'loss-text';
        const sign = isProfit ? '+' : '';

        const card = document.createElement('div');
        card.className = 'holding-card glass-panel';
        card.innerHTML = `
            <div class="holding-header">
                <div class="holding-symbol">${item.tradingsymbol}</div>
                <div class="holding-qty">${item.quantity} Shares</div>
            </div>
            <div class="holding-metrics">
                <div>
                    <div class="holding-price">${formatCurrency(item.last_price)}</div>
                    <div class="holding-avg">Avg: ${formatCurrency(item.average_price)}</div>
                </div>
                <div>
                    <div class="holding-pnl ${pnlClass}">${sign}${formatCurrency(pnl)}</div>
                    <div class="holding-avg ${pnlClass}">${sign}${pnlPercent.toFixed(2)}%</div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });

    // Update Overview Header
    const totalPnl = totalVal - totalInvested;
    const isTotalProfit = totalPnl >= 0;
    const totalSign = isTotalProfit ? '+' : '';
    const totalPnlPercent = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

    document.getElementById('total-value').innerText = formatCurrency(totalVal);
    document.getElementById('total-pnl').innerText = `${totalSign}${formatCurrency(totalPnl)} (${totalSign}${totalPnlPercent.toFixed(2)}%)`;
    document.getElementById('active-positions-count').innerText = holdings.length;

    const pill = document.getElementById('total-pnl-pill');
    pill.className = `pnl-pill ${isTotalProfit ? 'profit' : 'loss'}`;
    
    // Update Day's P&L
    const isDayProfit = totalDayPnl >= 0;
    const dayElement = document.getElementById('day-pnl');
    dayElement.innerText = `${isDayProfit ? '+' : ''}${formatCurrency(totalDayPnl)}`;
    dayElement.className = isDayProfit ? 'profit-text' : 'loss-text';
    // Remove the "Waiting for market data" subtitle
    dayElement.nextElementSibling.innerText = "Today's Performance";
};

const fetchHoldings = async () => {
    try {
        const grid = document.getElementById('holdings-grid');
        grid.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Syncing with Zerodha...</p></div>';

        const response = await fetch('/api/holdings');
        const json = await response.json();
        
        if (json.status === 'success') {
            renderHoldings(json.data);
        } else {
            console.error("API Error:", json);
            grid.innerHTML = `<div class="loading-state"><p>Error loading data: ${json.detail || 'Unknown error'}</p></div>`;
        }
    } catch (e) {
        console.error("Network Error:", e);
        document.getElementById('holdings-grid').innerHTML = '<div class="loading-state"><p>Network error. Make sure the backend is running.</p></div>';
    }
};

// Auto-fetch on load
document.addEventListener('DOMContentLoaded', fetchHoldings);
