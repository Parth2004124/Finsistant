import React, { useState, useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";
import './index.css';

let API_BASE = "http://127.0.0.1:8000/api";
try { API_BASE = localStorage.getItem("API_BASE") || API_BASE; } catch(e) {}

const fetchWithAuth = async (url, options = {}) => {
  let pwd = '';
  try { pwd = localStorage.getItem('EXECUTION_PASSWORD') || ''; } catch(e) {}
  if (!options.headers) options.headers = {};
  options.headers['Authorization'] = `Bearer ${pwd}`;
  options.headers['Content-Type'] = 'application/json';

  let res = await fetch(url, options);
  if (res.status === 401) {
    pwd = window.prompt('Execution requires authorization. Enter password:');
    if (!pwd) return null;
    try { localStorage.setItem('EXECUTION_PASSWORD', pwd); } catch(e) {}
    options.headers['Authorization'] = `Bearer ${pwd}`;
    res = await fetch(url, options);
  }
  return res;
};

const fmt = (n, d = 2) => {
  if (n === null || n === undefined) return "0";
  const num = Number(n);
  if (isNaN(num)) return "0";
  return num.toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
};
const fmtPct = (n) => {
  if (n === null || n === undefined) return "+0.00%";
  const num = Number(n);
  if (isNaN(num)) return "+0.00%";
  return (num >= 0 ? "+" : "") + num.toFixed(2) + "%";
};

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("React Error Boundary Caught:", error, errorInfo);
    this.setState({ errorInfo });
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: 'red', padding: '20px', background: '#222', minHeight: '100vh', fontFamily: 'monospace' }}>
          <h2>FATAL UI CRASH:</h2>
          <p>{this.state.error && this.state.error.toString()}</p>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </pre>
          <button onClick={() => window.location.reload()} style={{ padding: '10px', marginTop: '20px' }}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}

function ChartComponent({ data, selectedTrade }) {
  const chartContainerRef = useRef();
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const linesRef = useRef([]);
  const simSeriesRef = useRef(null);
  const trendLineRef = useRef(null);

  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: '#161a25' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: 'rgba(197, 203, 206, 0.8)' },
      timeScale: { borderColor: 'rgba(197, 203, 206, 0.8)' },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#4bffb5',
      downColor: '#ff4976',
      borderDownColor: '#ff4976',
      borderUpColor: '#4bffb5',
      wickDownColor: '#ff4976',
      wickUpColor: '#4bffb5',
    });
    seriesRef.current = candleSeries;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !seriesRef.current || !selectedTrade) return;
    
    // Clear old lines
    linesRef.current.forEach(l => seriesRef.current.removePriceLine(l));
    linesRef.current = [];
    
    if (simSeriesRef.current) {
        try { chartRef.current.removeSeries(simSeriesRef.current); } catch(e) {}
        simSeriesRef.current = null;
    }
    if (trendLineRef.current) {
        try { chartRef.current.removeSeries(trendLineRef.current); } catch(e) {}
        trendLineRef.current = null;
    }

    if (selectedTrade.ohlc && selectedTrade.ohlc.length > 0) {
      try {
        seriesRef.current.setData(selectedTrade.ohlc);

    const l1 = seriesRef.current.createPriceLine({ price: selectedTrade.target, color: '#39d353', lineWidth: 2, lineStyle: 0, title: 'Target (T)' });
    const l2 = seriesRef.current.createPriceLine({ price: selectedTrade.entry, color: '#58a6ff', lineWidth: 2, lineStyle: 0, title: 'Current Price' });
    const l3 = seriesRef.current.createPriceLine({ price: selectedTrade.stop, color: '#ff6b6b', lineWidth: 2, lineStyle: 0, title: 'Stop Loss (SL)' });
    
    linesRef.current = [l1, l2, l3];
    
    if (selectedTrade.simulated_ohlc && selectedTrade.simulated_ohlc.length > 0) {
        simSeriesRef.current = chartRef.current.addCandlestickSeries({
          upColor: '#1e90ff',
          downColor: '#000080',
          borderDownColor: '#000080',
          borderUpColor: '#1e90ff',
          wickDownColor: '#000080',
          wickUpColor: '#1e90ff',
        });
        simSeriesRef.current.setData(selectedTrade.simulated_ohlc);
        
        trendLineRef.current = chartRef.current.addLineSeries({ color: 'yellow', lineWidth: 2, lineStyle: 2 });
        const lastHist = selectedTrade.ohlc && selectedTrade.ohlc.length > 0 ? selectedTrade.ohlc[selectedTrade.ohlc.length - 1] : null;
        const lastSim = selectedTrade.simulated_ohlc[selectedTrade.simulated_ohlc.length - 1];
        
        if (lastHist && lastSim) {
            trendLineRef.current.setData([
               { time: lastHist.time, value: lastHist.close },
               { time: lastSim.time, value: lastSim.close }
            ]);
        }
    }

    chartRef.current.timeScale().fitContent();
      } catch (err) {
        console.error("Chart rendering error:", err);
      }
    }
  }, [selectedTrade]);

  return <div ref={chartContainerRef} style={{ width: '100%', height: '100%', minHeight: 300 }} />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}

function MainApp() {
  const [queue, setQueue] = useState([]);
  const [sells, setSells] = useState([]);
  const [rules, setRules] = useState([]);
  const [portfolio, setPortfolio] = useState({ stats: {}, holdings: [] });
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [activeTab, setActiveTab] = useState('All');
  
  const [showFundAccordion, setShowFundAccordion] = useState(false);
  const [fundAccordionSymbol, setFundAccordionSymbol] = useState(null);
  const [fundData, setFundData] = useState(null);
  const [fundLoading, setFundLoading] = useState(false);

  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [simulatingTrades, setSimulatingTrades] = useState({});
  
  const chatEndRef = useRef(null);

  const handleScan = () => {
    setIsScanning(true);
    const interval = setInterval(() => {
      fetch(`${API_BASE}/scan/progress?t=${Date.now()}`, {headers: {'ngrok-skip-browser-warning': 'true'}})
        .then(r => r.json())
        .then(d => {
          if (typeof d.progress === 'number') {
            setScanProgress(Math.floor(d.progress));
            if (d.progress >= 100) {
              clearInterval(interval);
              setTimeout(() => { setIsScanning(false); fetchState(); }, 1000);
            }
          }
        }).catch(e => console.error(e));
    }, 2000);
    fetchWithAuth(`${API_BASE}/scan`, {method: 'POST'}).catch(e => {
        clearInterval(interval);
        setIsScanning(false);
    });
  };

  const handleSimulate = (tradeId) => {
    setSimulatingTrades(prev => ({...prev, [tradeId]: true}));
    fetchWithAuth(`${API_BASE}/simulate/${tradeId}`, {method: 'POST'})
      .then(r => r.json())
      .then(d => {
         if (d.status !== 'success') {
             alert(d.detail || "Simulation failed to start.");
             setSimulatingTrades(prev => ({...prev, [tradeId]: false}));
         }
      }).catch(e => {
         console.error(e);
         setSimulatingTrades(prev => ({...prev, [tradeId]: false}));
      });
  };

  const fetchState = () => {
    fetch(`${API_BASE}/queue`, {headers: {'ngrok-skip-browser-warning': 'true'}}).then(r => r.json()).then(d => {
      if (d.data && Array.isArray(d.data)) {
        const parsePrice = (val) => {
          if (typeof val === 'number') return val;
          if (!val) return 0;
          const num = parseFloat(val.toString().replace(/[^0-9.-]+/g, ""));
          return isNaN(num) ? 0 : num;
        };
        const parseDurationBadge = (str) => {
          if (!str) return '3';
          const matches = str.match(/\d+/g);
          if (!matches) return '3';
          return Math.max(...matches.map(Number)).toString();
        };
        const buys = d.data.filter(t => t.status === 'PENDING' && t.transaction_type !== 'SELL').map(t => ({
          id: t.id, symbol: t.symbol, setup: t.setup_type, score: t.technical_score, confidence: t.confidence,
          entry: parsePrice(t.entry_zone), stop: parsePrice(t.stop_loss), target: parsePrice(t.target), rr: t.rr_ratio || 0,
          rationale: typeof t.rationale === 'string' && t.rationale.startsWith('{') ? JSON.parse(t.rationale) : (t.rationale || "No rationale provided"),
          qty: Math.max(1, Math.min(
              Math.floor(2000 / (parsePrice(t.entry_zone) - parsePrice(t.stop_loss))), // Max qty based on 2k risk
              Math.floor(5000 / parsePrice(t.entry_zone)) // Max qty based on 5k investment cap
          )),
          ohlc: t.ohlc,
          simulated_ohlc: t.trade_params?.simulated_ohlc || null,
          karnos_direction: t.karnos_direction,
          karnos_trend: t.karnos_trend,
          karnos_explanation: t.karnos_explanation,
          karlos_progress: t.trade_params?.karlos_progress || 0,
          duration: t.expected_hold_days || "3-5 days",
          badgeDuration: parseDurationBadge(t.expected_hold_days),
          type: 'BUY'
        }));
        
        buys.forEach(t => {
            if (t.simulated_ohlc) {
                setSimulatingTrades(prev => prev[t.id] ? {...prev, [t.id]: false} : prev);
                if (selectedTrade && selectedTrade.id === t.id && !selectedTrade.simulated_ohlc) {
                    setSelectedTrade(t);
                }
            } else if (simulatingTrades[t.id]) {
                if (selectedTrade && selectedTrade.id === t.id && selectedTrade.karlos_progress !== t.karlos_progress) {
                    setSelectedTrade(t);
                }
            }
        });

        const sellsQ = d.data.filter(t => t.status === 'PENDING' && t.transaction_type === 'SELL').map(t => ({
          id: t.id, symbol: t.symbol, setup: t.setup_type, score: t.technical_score, confidence: t.confidence,
          entry: parsePrice(t.entry_zone), stop: parsePrice(t.stop_loss), target: parsePrice(t.target), rr: t.rr_ratio || 0,
          rationale: typeof t.rationale === 'string' && t.rationale.startsWith('{') ? JSON.parse(t.rationale) : (t.rationale || "Risk flag breached."),
          qty: t.quantity || 0,
          ohlc: t.ohlc,
          type: 'SELL'
        }));
        setQueue(buys);
        setSells(sellsQ);
        if (buys.length > 0 && !selectedTrade) setSelectedTrade(buys[0]);
      }
    }).catch(e => console.error("fetchState error:", e));

    fetch(`${API_BASE}/auto-approve/rules`, {headers: {'ngrok-skip-browser-warning': 'true'}}).then(r => r.json()).then(d => {
      if (d.data) setRules(d.data);
    });
  };

  useEffect(() => {
    let interval;
    if (Object.values(simulatingTrades).some(v => v)) {
      interval = setInterval(() => {
        fetchState();
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [simulatingTrades]);

  useEffect(() => {
    const initApp = async () => {
      try {
        const resp = await fetch("https://raw.githubusercontent.com/Parth2004124/Finsistant/master/backend/ngrok_url.txt?t=" + Date.now());
        const text = await resp.text();
        if (text.startsWith("http")) {
          API_BASE = text.trim() + "/api";
          localStorage.setItem("API_BASE", API_BASE);
        }
      } catch(e) {
        console.error("Failed to fetch dynamic API URL:", e);
      }
      
      fetchState();
      fetch(`${API_BASE}/portfolio`, {headers: {'ngrok-skip-browser-warning': 'true'}}).then(r => r.json()).then(d => {
        if (d.status === "success") setPortfolio(d);
      }).catch(e => console.error("Portfolio fetch failed", e));
    };
    initApp();
  }, []);

  useEffect(() => {
    if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const sendChat = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatHistory(prev => [...prev, { role: "user", text: userMsg }]);
    setChatInput("");
    setIsChatLoading(true);

    try {
      let res = await fetch(`${API_BASE}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: userMsg })
      });
      let data = await res.json();
      setChatHistory(prev => [...prev, { role: "bot", text: data.reply }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: "bot", text: "Connection error." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleExecuteAll = () => {
    // We execute all BUY queue while checking if balance is sufficient
    // Actually, backend /api/approve can take an array, but we can filter it based on required funds locally first or let backend handle it
    const ids = queue.map(t => t.id);
    if(ids.length === 0) return;
    
    // We can just pass it to the backend and the backend will verify funds.
    fetchWithAuth(`${API_BASE}/approve`, { method: "POST", body: JSON.stringify({ trade_ids: ids, enforce_margin: true }) }).then(() => {
      fetchState();
    });
  };

  const executeTrade = (tradeId) => {
    fetchWithAuth(`${API_BASE}/approve`, { method: "POST", body: JSON.stringify({ trade_ids: [tradeId], enforce_margin: true }) }).then(() => {
      fetchState();
    });
  };

  // Keyboard shortcut for executing selected trade
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && selectedTrade && document.activeElement.tagName !== 'INPUT') {
        executeTrade(selectedTrade.id);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedTrade]);

  const pnlColor = portfolio.stats.pnl >= 0 ? '#39d353' : '#ff4976';
  const topSell = sells.length > 0 ? sells[0] : null;

  return (
    <div className="layout-container">
      {/* HEADER */}
      <header className="top-header">
        <div className="header-left">
          <div className="logo-box">TS</div>
          <div className="greeting">Good morning Parth!</div>
        </div>
        <div className="header-mid">
          Invested - {fmt(portfolio.stats.invested || 0, 0)} &nbsp;&nbsp; Current - {fmt(portfolio.stats.current || 0, 0)}
        </div>
        <div className="header-right">
          <span style={{ color: pnlColor }}>P/L - {fmt(portfolio.stats.pnl || 0, 0)}</span>
          <span style={{ marginLeft: 20 }}>Balance-{fmt(portfolio.stats.balance || 0, 0)}</span>
        </div>
      </header>

      {/* MAIN GRID */}
      <main className="main-grid">
        
        {/* LEFT PANEL */}
        <section className="left-panel">
          <div className="panel-header">
            <h3>Top picks today</h3>
            {isScanning ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 100, height: 6, background: '#333', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: '#fff', width: `${scanProgress}%`, transition: 'width 0.3s' }}></div>
                </div>
                <span style={{ fontSize: 12, color: '#888' }}>{scanProgress}%</span>
              </div>
            ) : (
              <button className="white-btn" onClick={handleScan}>Scan Now</button>
            )}
          </div>
          
          <div className="picks-table">
            {queue.map(t => (
              <div key={t.id} className={`pick-row ${selectedTrade?.id === t.id ? 'selected' : ''}`} onClick={() => setSelectedTrade(t)}>
                <div className="pick-symbol">{t.symbol}</div>
                <div className="pick-val bg-blue">{fmt(t.entry, 0)}</div>
                <div className="pick-val bg-green">{fmt(t.target, 0)}</div>
                <div className="pick-val bg-red">{fmt(t.stop, 0)}</div>
                <div className="pick-val bg-yellow">{t.badgeDuration}D</div>
              </div>
            ))}
            {queue.length === 0 && <div style={{ color: '#888', padding: '10px' }}>No pending buy setups</div>}
          </div>

          <div style={{ textAlign: 'right', marginTop: 10, marginBottom: 20 }}>
            <button className="execute-all-btn" onClick={handleExecuteAll}>EXECUTE ALL</button>
          </div>

          <div className="sell-box">
            {topSell ? (
              <>
                <div className="sell-text">SELL {topSell.symbol}</div>
                <button className="white-btn" onClick={() => executeTrade(topSell.id)}>Sell Now</button>
              </>
            ) : (
              <div className="sell-text" style={{ color: '#888' }}>NO SELL WARNINGS</div>
            )}
          </div>

          <div className="analysis-terminal">
            <div className="term-header">
              <span>Analysis</span>
              <div style={{ display: 'flex', gap: 4 }}>
                <span className="dot" style={{ background: '#ff5f56' }}></span>
                <span className="dot" style={{ background: '#ffbd2e' }}></span>
                <span className="dot" style={{ background: '#27c93f' }}></span>
              </div>
            </div>
            <div className="term-body">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ color: '#fff', margin: 0 }}>{selectedTrade ? `${selectedTrade.symbol} Analysis Terminal` : "No trade selected"}</h4>
                {selectedTrade && (
                    <button 
                        className="white-btn" 
                        style={{ padding: '2px 8px', background: showFundAccordion ? '#333' : 'transparent', color: '#fff', border: '1px solid #333', transition: 'all 0.2s' }}
                        onClick={() => toggleFundamentalAccordion(selectedTrade.symbol)}
                        title="Fundamental Analysis"
                    >
                        ⋮
                    </button>
                )}
              </div>
              
              {showFundAccordion && fundAccordionSymbol === selectedTrade?.symbol && (
                  <div style={{ marginBottom: 16, background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 16, animation: 'fadeIn 0.3s' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <span style={{ fontSize: 12, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>Fundamental Engine</span>
                    </div>
                    {fundLoading ? (
                         <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                            <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
                            <div style={{ color: '#8b949e', fontSize: 13 }}>Fetching from StockSight Engine...</div>
                         </div>
                    ) : fundData && !fundData.error ? (
                         <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                           <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                             <div style={{ background: '#0d1117', padding: 8, borderRadius: 6, border: '1px solid #30363d' }}>
                               <div style={{ fontSize: 10, color: '#8b949e' }}>Business Quality</div>
                               <div style={{ fontSize: 16, fontWeight: 'bold', color: '#fff' }}>{fundData.business}/40</div>
                             </div>
                             <div style={{ background: '#0d1117', padding: 8, borderRadius: 6, border: '1px solid #30363d' }}>
                               <div style={{ fontSize: 10, color: '#8b949e' }}>Economic Moat</div>
                               <div style={{ fontSize: 16, fontWeight: 'bold', color: '#fff' }}>{fundData.moat}/20</div>
                             </div>
                             <div style={{ background: '#0d1117', padding: 8, borderRadius: 6, border: '1px solid #30363d' }}>
                               <div style={{ fontSize: 10, color: '#8b949e' }}>Management</div>
                               <div style={{ fontSize: 16, fontWeight: 'bold', color: '#fff' }}>{fundData.management}/20</div>
                             </div>
                             <div style={{ background: '#0d1117', padding: 8, borderRadius: 6, border: '1px solid #30363d' }}>
                               <div style={{ fontSize: 10, color: '#8b949e' }}>Risk Profile</div>
                               <div style={{ fontSize: 16, fontWeight: 'bold', color: '#fff' }}>{fundData.risk}/20</div>
                             </div>
                           </div>
                           <div style={{ background: '#238636', color: '#fff', padding: '8px 12px', borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                             <div>
                               <div style={{ fontSize: 12, opacity: 0.9 }}>Total Score</div>
                               <div style={{ fontSize: 12, fontWeight: 'bold' }}>{fundData.explanation}</div>
                             </div>
                             <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                               {fundData.total}/99
                             </div>
                           </div>
                         </div>
                    ) : (
                         <div style={{ color: '#ff6b6b', fontSize: 13, padding: '10px 0' }}>
                            {fundData?.error || "Failed to fetch fundamental data."}
                         </div>
                    )}
                  </div>
              )}

              {selectedTrade ? (
                <div className="term-content">
                  {typeof selectedTrade.rationale === 'string' 
                    ? selectedTrade.rationale.split('\n').map((line, i) => <div key={i} style={{ marginBottom: 4 }}>{line}</div>)
                    : <div style={{ marginBottom: 4 }}>{selectedTrade.rationale?.why_lucrative || "No rationale provided"}</div>}
                  <div style={{ marginTop: 12 }}>Verdict: BUY</div>
                  <div>QTY: {selectedTrade.qty} Shares</div>
                  <div>Amt = {fmt(selectedTrade.qty * selectedTrade.entry)}</div>
                  <div>Confidence: {selectedTrade.confidence}%</div>
                  <div>Expected Duration: {selectedTrade.duration}</div>
                  <div style={{ marginTop: 16 }}>
                    <button 
                       className="white-btn" 
                       style={{ background: '#1e90ff', color: 'white', border: 'none', padding: '6px 12px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
                       disabled={simulatingTrades[selectedTrade.id] || selectedTrade.simulated_ohlc}
                       onClick={() => handleSimulate(selectedTrade.id)}
                    >
                      {simulatingTrades[selectedTrade.id] ? (
                        <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 6 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }}></div>
                            <span>Simulating... {selectedTrade.karlos_progress || 0}%</span>
                          </div>
                          <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.2)', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ width: `${selectedTrade.karlos_progress || 0}%`, height: '100%', background: '#fff', transition: 'width 0.5s ease-in-out' }}></div>
                          </div>
                        </div>
                      ) : selectedTrade.simulated_ohlc ? (
                        "Simulation Complete"
                      ) : (
                        "Simulate with Karlos AI"
                      )}
                    </button>
                  </div>
                  <div className="blink" style={{ marginTop: 16 }}>PRESS ENTER TO EXECUTE</div>
                </div>
              ) : (
                <div style={{ color: '#888' }}>Select a pick to view analysis</div>
              )}
            </div>
          </div>
        </section>

        {/* MIDDLE PANEL */}
        <section className="middle-panel">
          <div className="chart-wrapper">
             <div className="chart-header">
               <span style={{ fontSize: 12, fontWeight: 700 }}>{selectedTrade?.symbol || 'INDEX'} NSE (1D)</span>
             </div>
             <ChartComponent selectedTrade={selectedTrade} />
          </div>

          <div className="rules-section">
            <div className="panel-header">
              <h3>Auto Execution Rules</h3>
              <button className="white-btn">New Rule Set</button>
            </div>
            <div className="rules-list">
              {rules.map((r, i) => (
                <div key={r.rule_id || i} className="rule-row" style={{ borderColor: r.active ? '#39d353' : '#fff' }}>
                  <div>{r.setup_type === '*' ? 'Rule Set ' + (i+1) : r.setup_type}</div>
                  {r.active && <div style={{ color: '#39d353', fontWeight: 'bold' }}>ACTIVE</div>}
                </div>
              ))}
              {rules.length === 0 && (
                <>
                  <div className="rule-row" style={{ borderColor: '#39d353' }}>
                    <div>Strict Breakout Rules (Score &gt; 80)</div>
                    <div style={{ color: '#39d353', fontWeight: 'bold' }}>ACTIVE</div>
                  </div>
                  <div className="rule-row">
                    <div>Momentum Runners (Score &gt; 75)</div>
                  </div>
                </>
              )}
            </div>
          </div>
          
          <div className="legend-box">
             <div className="legend-item bg-blue">CP</div>
             <div className="legend-item bg-green">TP</div>
             <div className="legend-item bg-red">SL</div>
             <div className="legend-item bg-yellow">HD</div>
          </div>
        </section>

        {/* RIGHT PANEL */}
        <section className="right-panel">
          <div className="holdings-section">
            <div className="holdings-tabs">
              <span className="active-tab">All</span>
              <span>Equity</span>
              <span>Mutual funds</span>
            </div>
            <div className="holdings-header">
              <h3>Holdings</h3>
              <div className="search-bar">🔍 Search</div>
            </div>
            <table className="holdings-table">
              <thead>
                <tr>
                  <th>Instrument</th>
                  <th>Qty.</th>
                  <th>LTP</th>
                  <th>P&L</th>
                  <th>Net chg</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map((h, i) => (
                  <tr key={i}>
                    <td>{h.instrument}</td>
                    <td>{h.qty}</td>
                    <td>{fmt(h.ltp)}</td>
                    <td style={{ color: h.pnl >= 0 ? '#39d353' : '#ff4976' }}>{fmt(h.pnl)}</td>
                    <td style={{ color: h.net_chg >= 0 ? '#39d353' : '#ff4976' }}>{fmtPct(h.net_chg)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="chat-section">
            <div className="explore-text">Explore what's possible</div>
            <div className="chat-actions">
              <button onClick={() => setChatInput("Deep search ONGC fundamentals")}>🔍 Deep Search</button>
              <button onClick={() => setChatInput("Analyze my Watchlist")}>📈 Analyze my Watchlist</button>
            </div>
            
            <div className="chat-history">
               {chatHistory.map((msg, i) => (
                 <div key={i} className={`chat-msg ${msg.role}`}>{msg.text}</div>
               ))}
               {isChatLoading && <div className="chat-msg bot">Thinking...</div>}
               <div ref={chatEndRef} />
            </div>

            <div className="chat-input-box">
              <input 
                type="text" 
                placeholder="Ask anything" 
                value={chatInput} 
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendChat()}
              />
              <button onClick={sendChat} className="send-btn">↑</button>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
