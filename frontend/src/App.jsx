import React, { useState, useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";
import './index.css';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';

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

function ChartComponent({ data, selectedTrade, chartType = 'candle' }) {
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

    if (chartType === 'line') {
      const lineSeries = chart.addLineSeries({
        color: '#1e90ff',
        lineWidth: 2,
      });
      seriesRef.current = lineSeries;
    } else {
      const candleSeries = chart.addCandlestickSeries({
        upColor: '#39d353',
        downColor: '#ff4976',
        borderDownColor: '#ff4976',
        borderUpColor: '#39d353',
        wickDownColor: '#ff4976',
        wickUpColor: '#39d353',
      });
      seriesRef.current = candleSeries;
    }

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
        if (chartType === 'line') {
          const lineData = selectedTrade.ohlc.map(d => ({ time: d.time, value: d.close || d.value }));
          seriesRef.current.setData(lineData);
        } else {
          seriesRef.current.setData(selectedTrade.ohlc);
        }

    if (selectedTrade.target) {
      const l1 = seriesRef.current.createPriceLine({ price: selectedTrade.target, color: '#39d353', lineWidth: 2, lineStyle: 0, title: 'Target (T)' });
      linesRef.current.push(l1);
    }
    if (selectedTrade.entry) {
      const l2 = seriesRef.current.createPriceLine({ price: selectedTrade.entry, color: '#58a6ff', lineWidth: 2, lineStyle: 0, title: 'Current Price' });
      linesRef.current.push(l2);
    }
    if (selectedTrade.stop) {
      const l3 = seriesRef.current.createPriceLine({ price: selectedTrade.stop, color: '#ff6b6b', lineWidth: 2, lineStyle: 0, title: 'Stop Loss (SL)' });
      linesRef.current.push(l3);
    }
    
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
    
    if (selectedTrade.regressionPoints && selectedTrade.regressionPoints.length > 0) {
        const regSeries = chartRef.current.addLineSeries({ color: '#ffeb3b', lineWidth: 2 });
        const upperSeries = chartRef.current.addLineSeries({ color: 'rgba(255, 235, 59, 0.4)', lineWidth: 1, lineStyle: 2 });
        const lowerSeries = chartRef.current.addLineSeries({ color: 'rgba(255, 235, 59, 0.4)', lineWidth: 1, lineStyle: 2 });
        
        regSeries.setData(selectedTrade.regressionPoints.map(p => ({ time: p.time, value: p.value })));
        upperSeries.setData(selectedTrade.regressionPoints.map(p => ({ time: p.time, value: p.upper })));
        lowerSeries.setData(selectedTrade.regressionPoints.map(p => ({ time: p.time, value: p.lower })));
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
  const [sessionRenewing, setSessionRenewing] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isChatPopupOpen, setIsChatPopupOpen] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [activeTab, setActiveTab] = useState('All');
  const [simulatingTrades, setSimulatingTrades] = useState({});
  const [activeAppTab, setActiveAppTab] = useState('Terminal');
  const [optReport, setOptReport] = useState(null);
  const [isOptGenerating, setIsOptGenerating] = useState(false);

  // --- Watchlist State ---
  const [watchlist, setWatchlist] = useState([]);
  const [wlSearch, setWlSearch] = useState("");
  const [wlSuggestions, setWlSuggestions] = useState([]);
  const [selectedWlSymbol, setSelectedWlSymbol] = useState(null);
  const [wlOhlc, setWlOhlc] = useState(null);
  const [isWlAutoAdding, setIsWlAutoAdding] = useState(false);
  const [isWlQuantAnalyzing, setIsWlQuantAnalyzing] = useState(false);
  const [stockyMsg, setStockyMsg] = useState("");
  const [stockyReply, setStockyReply] = useState(null);
  const [stockyLoading, setStockyLoading] = useState(false);
  const [showWlFundAccordion, setShowWlFundAccordion] = useState(false);
  const [showWlPortersAccordion, setShowWlPortersAccordion] = useState(false);

  const handleTradeSelect = async (t) => {
    setSelectedTrade(t);
    try {
      const res = await fetch(`${API_BASE}/chart/${t.symbol}`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      if (data.status === 'success') {
        setSelectedTrade(prev => (prev && prev.id === t.id ? { ...prev, ohlc: data.data } : prev));
      } else {
        setSelectedTrade(prev => (prev && prev.id === t.id ? { ...prev, ohlc: [{ error: data.detail || "Unknown error" }] } : prev));
      }
    } catch (err) {
      console.error(err);
      setSelectedTrade(prev => (prev && prev.id === t.id ? { ...prev, ohlc: [{ error: err.message }] } : prev));
    }
  };

  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_BASE}/watchlist`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      if (data.status === 'success') {
        setWatchlist(data.data);
      }
    } catch (err) {
      console.error("Watchlist fetch error:", err);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleWlAdd = async (e) => {
    if (e.key === 'Enter' && wlSearch.trim()) {
      try {
        await fetch(`${API_BASE}/watchlist/${wlSearch.trim()}`, { method: 'POST' });
        setWlSearch("");
        setWlSuggestions([]);
        fetchWatchlist();
      } catch (err) { console.error(err); }
    }
  };

  const handleWlSearchChange = async (val) => {
    setWlSearch(val);
    if (!val.trim()) {
      setWlSuggestions([]);
      return;
    }
    try {
      let res = await fetch(`${API_BASE}/search?q=${val}`);
      let data = await res.json();
      if (data.status === 'success') {
        setWlSuggestions(data.results);
      }
    } catch(e) {}
  };

  const handleWlSuggestionClick = async (sym) => {
    try {
      await fetch(`${API_BASE}/watchlist/${sym}`, { method: 'POST' });
      setWlSearch("");
      setWlSuggestions([]);
      fetchWatchlist();
    } catch (err) { console.error(err); }
  };

  const handleWlRemove = async (sym) => {
    try {
      await fetch(`${API_BASE}/watchlist/${sym}`, { method: 'DELETE' });
      if (selectedWlSymbol === sym) setSelectedWlSymbol(null);
      fetchWatchlist();
    } catch (err) { console.error(err); }
  };

  const handlePortfolioOptimization = async () => {
    setIsOptGenerating(true);
    setOptReport(null);
    try {
        await fetch(`${API_BASE}/portfolio/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(portfolio)
        });
        
        const poll = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/portfolio/optimization_status`, {headers: {'ngrok-skip-browser-warning': 'true'}});
                const data = await res.json();
                if (data.status === 'success') {
                    clearInterval(poll);
                    setOptReport(data.report);
                    setIsOptGenerating(false);
                }
            } catch(e) {}
        }, 3000);
    } catch (e) {
        console.error("AI Portfolio Optimization failed", e);
        setIsOptGenerating(false);
    }
  };

  const handleWlQuantAnalyze = async () => {
    if (!selectedWlSymbol) return;
    setIsWlQuantAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/watchlist/quant-analyze/${selectedWlSymbol}`, { method: 'POST' });
      await res.json();
      
      const poll = setInterval(async () => {
          const w_res = await fetch(`${API_BASE}/watchlist`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
          const w_data = await w_res.json();
          if (w_data.status === 'success') {
              const item = w_data.data.find(x => x.symbol === selectedWlSymbol);
              if (item && item.quant_report) {
                  clearInterval(poll);
                  setWatchlist(w_data.data);
                  setIsWlQuantAnalyzing(false);
              }
          }
      }, 3000);
    } catch (err) { 
        console.error(err); 
        setIsWlQuantAnalyzing(false);
    }
  };

  const handleWlAutoAdd = async () => {
    setIsWlAutoAdding(true);
    try {
      const res = await fetch(`${API_BASE}/watchlist/auto-add`, { method: 'POST' });
      await res.json();
      fetchWatchlist();
    } catch (err) { console.error(err); }
    setIsWlAutoAdding(false);
  };

  const handleWlSelect = async (sym) => {
    setSelectedWlSymbol(sym);
    setWlOhlc(null);
    fetchFundamentalData(sym);
    try {
      const res = await fetch(`${API_BASE}/chart/${sym}`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      if (data.status === 'success') {
        setWlOhlc(data.data);
      } else {
        setWlOhlc([{ error: data.detail || "Unknown error" }]);
      }
    } catch (err) { 
      console.error(err); 
      setWlOhlc([{ error: err.message }]);
    }
  };

  const handleStockyChat = async (e) => {
    if (e.key === 'Enter' && stockyMsg.trim()) {
      setStockyLoading(true);
      try {
        const res = await fetch(`${API_BASE}/stocky`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: stockyMsg })
        });
        const data = await res.json();
        if (data.status === 'success') {
          setStockyReply(data.reply);
          setStockyMsg("");
        }
      } catch (err) { console.error(err); }
      setStockyLoading(false);
    }
  };
  
  const [showFundAccordion, setShowFundAccordion] = useState(false);
  const [fundAccordionSymbol, setFundAccordionSymbol] = useState(null);
  const [fundData, setFundData] = useState(null);
  const [fundLoading, setFundLoading] = useState(false);
  const [holdingFundData, setHoldingFundData] = useState({});
  const [holdingFundLoading, setHoldingFundLoading] = useState({});
  const [expandedHoldings, setExpandedHoldings] = useState({});

  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);

  // Background scanner for holdings
  useEffect(() => {
      if (!portfolio || !portfolio.holdings || portfolio.holdings.length === 0) return;
      
      const scanHoldingsSequentially = async () => {
          for (let h of portfolio.holdings) {
              const sym = h.instrument;
              // Skip if already scanned or currently scanning
              if (holdingFundData[sym] || holdingFundLoading[sym]) continue;
              
              setHoldingFundLoading(prev => ({...prev, [sym]: true}));
              try {
                  // Check if it already exists
                  let res = await fetch(`${API_BASE}/fundamentals/${sym}?is_holding=true`, {headers: {'ngrok-skip-browser-warning': 'true'}});
                  let data = await res.json();
                  if (data.status === 'success' && data.data) {
                      setHoldingFundData(prev => ({...prev, [sym]: data.data}));
                      setHoldingFundLoading(prev => ({...prev, [sym]: false}));
                  } else {
                      // Trigger scan
                      await fetch(`${API_BASE}/fundamentals/${sym}`, {
                          method: 'POST', 
                          headers: {'ngrok-skip-browser-warning': 'true', 'Content-Type': 'application/json'},
                          body: JSON.stringify({is_holding: true})
                      });
                      
                      // Poll until success or timeout (try up to 15 times, i.e., 45s)
                      let attempts = 0;
                      while (attempts < 15) {
                          await new Promise(r => setTimeout(r, 3000));
                          let r2 = await fetch(`${API_BASE}/fundamentals/${sym}?is_holding=true`, {headers: {'ngrok-skip-browser-warning': 'true'}});
                          let d2 = await r2.json();
                          if (d2.status === 'success' && d2.data) {
                              setHoldingFundData(prev => ({...prev, [sym]: d2.data}));
                              setHoldingFundLoading(prev => ({...prev, [sym]: false}));
                              break;
                          }
                          attempts++;
                      }
                      if (attempts >= 15) {
                          setHoldingFundData(prev => ({...prev, [sym]: {error: "Timed out"}}));
                          setHoldingFundLoading(prev => ({...prev, [sym]: false}));
                      }
                  }
              } catch (e) {
                  setHoldingFundData(prev => ({...prev, [sym]: {error: "Failed"}}));
                  setHoldingFundLoading(prev => ({...prev, [sym]: false}));
              }
              // Wait 1 second between processing different holdings to spread load
              await new Promise(r => setTimeout(r, 1000));
          }
      };
      scanHoldingsSequentially();
  }, [portfolio.holdings]);

  
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
                    setSelectedTrade(prev => ({...prev, simulated_ohlc: t.simulated_ohlc, karlos_progress: t.karlos_progress}));
                }
            } else if (simulatingTrades[t.id]) {
                if (selectedTrade && selectedTrade.id === t.id && selectedTrade.karlos_progress !== t.karlos_progress) {
                    setSelectedTrade(prev => ({...prev, karlos_progress: t.karlos_progress}));
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
        if (buys.length > 0 && !selectedTrade) {
          handleTradeSelect(buys[0]);
        }
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
      const fetchPortfolioWithRetry = () => {
        fetch(`${API_BASE}/portfolio`, {headers: {'ngrok-skip-browser-warning': 'true'}})
          .then(async r => {
              if (r.status === 503) {
                  setSessionRenewing(true);
                  setTimeout(fetchPortfolioWithRetry, 5000);
                  return null;
              }
              setSessionRenewing(false);
              return r.json();
          })
          .then(d => {
            if (d && d.status === "success") setPortfolio(d);
          }).catch(e => console.error("Portfolio fetch failed", e));
      };
      fetchPortfolioWithRetry();
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
      let res = await fetch(`${API_BASE}/stocky`, {
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

  const fetchFundamentalData = (symbol) => {
      setFundLoading(true);
      setFundData(null);
      const checkFund = async () => {
        try {
          let res = await fetch(`${API_BASE}/fundamentals/${symbol}?is_holding=false`, {headers: {'ngrok-skip-browser-warning': 'true'}});
          let data = await res.json();
          if (data.status === 'success' && data.data) {
             setFundData(data.data);
             setFundLoading(false);
          } else {
             await fetch(`${API_BASE}/fundamentals/${symbol}`, {
                 method: 'POST', 
                 headers: {'ngrok-skip-browser-warning': 'true', 'Content-Type': 'application/json'},
                 body: JSON.stringify({is_holding: false})
             });
             const intId = setInterval(async () => {
                 try {
                     let r2 = await fetch(`${API_BASE}/fundamentals/${symbol}?is_holding=false`, {headers: {'ngrok-skip-browser-warning': 'true'}});
                     let d2 = await r2.json();
                     if (d2.status === 'success' && d2.data) {
                         setFundData(d2.data);
                         setFundLoading(false);
                         clearInterval(intId);
                     }
                 } catch(e){}
             }, 3000);
             setTimeout(() => {
                 clearInterval(intId);
                 setFundLoading((prev) => {
                     if (prev) setFundData({error: "Fundamental engine timed out."});
                     return false;
                 });
             }, 45000);
          }
        } catch(e) {
          setFundLoading(false);
          setFundData({error: "Failed to connect to backend."});
        }
      };
      checkFund();
  };

  const toggleFundamentalAccordion = (symbol) => {
    if (fundAccordionSymbol === symbol && showFundAccordion) {
      setShowFundAccordion(false);
      setFundAccordionSymbol(null);
    } else {
      setFundAccordionSymbol(symbol);
      setShowFundAccordion(true);
      fetchFundamentalData(symbol);
    }
  };



  return (
    <div className="layout-container">
      {/* HEADER */}
      <header className="top-header">
        <div className="header-left">
          <div className="logo-box">TS</div>
          <div className="greeting">{new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening'} Parth!</div>
        </div>
        <div className="header-mid">
          {sessionRenewing ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }}></div>
                <span style={{ color: '#1e90ff' }}>Renewing Broker Session...</span>
            </div>
          ) : (
            <>Invested - {fmt(portfolio.stats.invested || 0, 0)} &nbsp;&nbsp; Current - {fmt(portfolio.stats.current || 0, 0)}</>
          )}
        </div>
        <div className="header-right">
          {!sessionRenewing && (
            <>
              <span style={{ color: pnlColor }}>P/L - {fmt(portfolio.stats.pnl || 0, 0)}</span>
              <span style={{ marginLeft: 20 }}>Balance-{fmt(portfolio.stats.balance || 0, 0)}</span>
            </>
          )}
        </div>
      </header>

      {/* TOP NAVIGATION BAR */}
      <nav className="top-nav-bar">
        <div 
          className={`nav-tab ${activeAppTab === 'Terminal' ? 'active' : ''}`}
          onClick={() => setActiveAppTab('Terminal')}
        >
          Terminal
        </div>
        <div 
          className={`nav-tab ${activeAppTab === 'Watchlist' ? 'active' : ''}`}
          onClick={() => setActiveAppTab('Watchlist')}
        >
          Watchlist
        </div>
        <div 
          className={`nav-tab ${activeAppTab === 'Analytics' ? 'active' : ''}`}
          onClick={() => setActiveAppTab('Analytics')}
        >
          Analytics
        </div>
      </nav>

      {/* MAIN CONTENT AREA */}
      {activeAppTab === 'Terminal' && (
        <main className="main-grid">
        
        {/* LEFT PANEL */}
        <section className="left-panel">
          <div className="panel-header">
            <h3>Top picks today</h3>
            <button className="white-btn" onClick={handleScan}>
              {isScanning ? `Scanning... ${scanProgress}%` : "Scan Now"}
            </button>
          </div>
          
          <div className="picks-table">
            {queue.map(t => (
              <div key={t.id} className={`pick-row ${selectedTrade?.id === t.id ? 'selected' : ''}`} onClick={() => handleTradeSelect(t)}>
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
                            <div style={{ color: '#8b949e', fontSize: 13 }}>Running Independent Fundamental Engine...</div>
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
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {portfolio.holdings.map((h, i) => [
                  <tr key={`row-${i}`}>
                    <td>{h.instrument}</td>
                    <td>{h.qty}</td>
                    <td>{fmt(h.ltp)}</td>
                    <td style={{ color: h.pnl >= 0 ? '#39d353' : '#ff4976' }}>{fmt(h.pnl)}</td>
                    <td style={{ color: h.net_chg >= 0 ? '#39d353' : '#ff4976' }}>{fmtPct(h.net_chg)}</td>
                    <td>
                      <button 
                          className="white-btn" 
                          style={{ padding: '2px 8px', background: expandedHoldings[h.instrument] ? '#333' : 'transparent', color: '#fff', border: '1px solid #333', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: 6 }}
                          onClick={() => setExpandedHoldings(prev => ({...prev, [h.instrument]: !prev[h.instrument]}))}
                          title="Fundamental Analysis"
                      >
                          {holdingFundLoading[h.instrument] ? <div className="spinner" style={{ width: 10, height: 10, borderWidth: 1 }}></div> : null}
                          ?
                      </button>
                    </td>
                  </tr>,
                  expandedHoldings[h.instrument] && (
                    <tr key={`acc-${i}`}>
                      <td colSpan="6" style={{ padding: '10px', background: '#111216', borderBottom: '1px solid #30363d' }}>
                        {holdingFundLoading[h.instrument] ? (
                           <div style={{ color: '#8b949e', fontSize: 12 }}>Running Independent Fundamental Engine...</div>
                        ) : holdingFundData[h.instrument] && !holdingFundData[h.instrument].error ? (
                           <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fff' }}>
                                 <span>Score: <strong>{holdingFundData[h.instrument].total}/99</strong></span>
                                 <span>{holdingFundData[h.instrument].explanation}</span>
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e' }}>
                                 <span>Biz: {holdingFundData[h.instrument].business}</span>
                                 <span>Moat: {holdingFundData[h.instrument].moat}</span>
                                 <span>Mgmt: {holdingFundData[h.instrument].management}</span>
                                 <span>Risk: {holdingFundData[h.instrument].risk}</span>
                              </div>
                           </div>
                        ) : (
                           <div style={{ color: '#ff6b6b', fontSize: 12 }}>{holdingFundData[h.instrument]?.error || "Failed to fetch fundamental data."}</div>
                        )}
                      </td>
                    </tr>
                  )
                ])}
              </tbody>
            </table>
            <div style={{ padding: '10px' }}>
                <button 
                  className="white-btn" 
                  style={{ width: '100%', fontSize: 11 }}
                  onClick={async () => {
                      await fetch(`${API_BASE}/fundamentals/rescan-holdings`, {method: 'POST'});
                      setHoldingFundData({});
                      // Trick to re-trigger the useEffect by copying the array
                      setPortfolio(prev => ({...prev, holdings: [...prev.holdings]}));
                  }}
                >
                  ↻ Re-Scan Fundamentals
                </button>
            </div>
          </div>

          <div className="chat-section">
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px' }}>Stocky AI</h3>
            <div className="explore-text">Explore what's possible</div>
            <div className="chat-actions">
              <button onClick={() => setChatInput("Deep search ONGC fundamentals")}>🔍 Deep Search</button>
              <button onClick={() => setChatInput("Analyze my Watchlist")}>📈 Analyze my Watchlist</button>
            </div>
            
            <div className="chat-history">
               {chatHistory.map((msg, i) => (
                 <div key={i} className={`chat-msg ${msg.role}`} dangerouslySetInnerHTML={{ __html: msg.text }}></div>
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
      )}

      {activeAppTab === 'Watchlist' && (
        <main className="main-grid" style={{ gridTemplateColumns: 'minmax(0, 7fr) minmax(0, 3fr)' }}>
          
          <section className="middle-panel" style={{ borderRight: '1px solid #30363d', paddingRight: '20px' }}>
             {selectedWlSymbol ? (
                <>
                  <div className="chart-wrapper" style={{ marginBottom: '20px' }}>
                    <div className="chart-header">
                       <span style={{ fontSize: 12, fontWeight: 700 }}>{selectedWlSymbol} NSE (1D)</span>
                    </div>
                    {wlOhlc && wlOhlc.length > 0 && !wlOhlc[0].error ? (
                        <ChartComponent selectedTrade={{ 
                            symbol: selectedWlSymbol, 
                            ohlc: wlOhlc,
                            regressionPoints: watchlist.find(i => i.symbol === selectedWlSymbol)?.regression_points ? JSON.parse(watchlist.find(i => i.symbol === selectedWlSymbol).regression_points) : null
                        }} chartType="line" />
                    ) : wlOhlc && wlOhlc.length > 0 && wlOhlc[0].error ? (
                        <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ff5f56', fontStyle: 'italic', padding: 20, textAlign: 'center' }}>
                            Error fetching chart: {wlOhlc[0].error}
                        </div>
                    ) : (
                        <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e', fontStyle: 'italic' }}>
                            Fetching chart data...
                        </div>
                    )}
                  </div>
                  
                  <div className="analytics-dashboard-grid" style={{ marginTop: '20px' }}>
                    {fundLoading ? (
                       <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 12, padding: '20px', color: '#8b949e' }}>
                         <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
                         Analyzing Fundamentals & Moat...
                       </div>
                    ) : fundData && !fundData.error ? (
                       <>
                         <div className="analytics-col">
                           <div className="analytics-col-title">Internal Scoring</div>
                           <div className="score-row"><span>Business</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.business/40)*100}%`, background: '#39d353' }}></div></div></div>
                           <div className="score-row"><span>Moat</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.moat/20)*100}%`, background: '#58a6ff' }}></div></div></div>
                           <div className="score-row"><span>Management</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.management/20)*100}%`, background: '#d2a8ff' }}></div></div></div>
                           <div className="score-row"><span>Risk</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.risk/20)*100}%`, background: '#ff7b72' }}></div></div></div>
                         </div>
                         
                         {fundData.porters && (
                           <div className="analytics-col">
                             <div className="analytics-col-title">Porter's 5 Forces</div>
                             <div className="score-row"><span>Entrants</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.porters.entrants/20)*100}%`, background: '#8957e5' }}></div></div></div>
                             <div className="score-row"><span>Suppliers</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.porters.suppliers/20)*100}%`, background: '#8957e5' }}></div></div></div>
                             <div className="score-row"><span>Buyers</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.porters.buyers/20)*100}%`, background: '#8957e5' }}></div></div></div>
                             <div className="score-row"><span>Substitutes</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.porters.substitutes/20)*100}%`, background: '#8957e5' }}></div></div></div>
                             <div className="score-row"><span>Rivalry</span><div className="score-bar-container"><div className="score-bar-fill" style={{ width: `${(fundData.porters.rivalry/20)*100}%`, background: '#8957e5' }}></div></div></div>
                           </div>
                         )}

                         {fundData.ratios && (
                           <div className="analytics-col">
                             <div className="analytics-col-title">Key Ratios</div>
                             <div className="ratios-grid">
                               <div className="ratio-card"><span className="ratio-label">P/E Ratio</span><span className="ratio-value">{fundData.ratios.pe ? fundData.ratios.pe.toFixed(2) : '-'}</span></div>
                               <div className="ratio-card"><span className="ratio-label">ROE</span><span className="ratio-value">{fundData.ratios.roe ? fundData.ratios.roe.toFixed(1) + '%' : '-'}</span></div>
                               <div className="ratio-card"><span className="ratio-label">Debt/Eq</span><span className="ratio-value">{fundData.ratios.debtToEquity ? fundData.ratios.debtToEquity.toFixed(2) : '-'}</span></div>
                               <div className="ratio-card"><span className="ratio-label">Sales Gr.</span><span className="ratio-value">{fundData.ratios.salesGrowth ? fundData.ratios.salesGrowth.toFixed(1) + '%' : '-'}</span></div>
                             </div>
                           </div>
                         )}
                         
                         {fundData.nlp && (
                           <div className="nlp-insight-box">
                             <strong>Stocky AI Insight:</strong> {fundData.nlp}
                           </div>
                         )}
                         
                         {isWlQuantAnalyzing && (
                           <div className="nlp-insight-box" style={{ background: '#161b22', borderLeft: '4px solid #1e90ff', padding: '30px', marginTop: '15px', gridColumn: '1 / -1', borderRadius: '8px' }}>
                             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' }}>
                               <div className="spinner" style={{ width: 30, height: 30, borderWidth: 3 }}></div>
                               <div style={{ color: '#8b949e', fontStyle: 'italic', fontSize: '13px' }}>Synthesizing CFA Visual Dashboard for {selectedWlSymbol}...</div>
                               <div style={{ width: '60%', height: '6px', background: '#30363d', borderRadius: '4px', overflow: 'hidden', marginTop: '10px' }}>
                                 <div style={{ height: '100%', background: '#1e90ff', animation: 'quantProgress 12s cubic-bezier(0.1, 0.7, 1.0, 0.1) forwards' }}></div>
                               </div>
                             </div>
                           </div>
                         )}
                         
                         {!isWlQuantAnalyzing && (() => {
                           const qr = watchlist.find(i => i.symbol === selectedWlSymbol)?.quant_report;
                           if (!qr) return null;
                           let parsed;
                           try {
                             parsed = JSON.parse(qr);
                           } catch (e) {
                             return (
                               <div className="nlp-insight-box" style={{ background: '#161b22', borderLeft: '4px solid #1e90ff', padding: '15px', marginTop: '15px', gridColumn: '1 / -1' }}>
                                 <div style={{ color: '#1e90ff', fontWeight: 'bold', marginBottom: '10px', fontSize: '14px' }}>CFA Quantitative Research Report</div>
                                 <div style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: '#c9d1d9', lineHeight: '1.6' }}>{qr}</div>
                               </div>
                             );
                           }
                           return (
                             <div className="nlp-insight-box" style={{ background: '#161b22', borderLeft: '4px solid #1e90ff', padding: '20px', marginTop: '15px', gridColumn: '1 / -1', borderRadius: '8px' }}>
                               <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '15px' }}>
                                  <div style={{ color: '#1e90ff', fontWeight: 'bold', fontSize: '15px' }}>CFA Quant & Fundamental Summary</div>
                               </div>
                               
                               <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '15px' }}>
                                 {parsed.kpis && parsed.kpis.map((kpi, idx) => (
                                   <div key={idx} style={{ background: '#0d1117', border: `1px solid ${kpi.color || '#30363d'}`, borderRadius: '8px', padding: '12px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                                     <div style={{ color: '#8b949e', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 'bold', letterSpacing: '0.5px' }}>{kpi.label}</div>
                                     <div style={{ color: kpi.color || '#fff', fontSize: '15px', fontWeight: 'bold' }}>{kpi.value}</div>
                                   </div>
                                 ))}
                               </div>
                               
                               <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
                                 {parsed.doughnut_chart && parsed.doughnut_chart.length > 0 && (
                                    <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', height: '220px', minWidth: 0 }}>
                                      <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '5px', textAlign: 'center', fontWeight: 'bold' }}>Conviction Score</div>
                                      <ResponsiveContainer width="99%" height={170}>
                                        <PieChart>
                                          <Pie data={parsed.doughnut_chart} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" stroke="none">
                                            {parsed.doughnut_chart.map((entry, index) => (
                                              <Cell key={`cell-${index}`} fill={entry.fill || '#fff'} />
                                            ))}
                                          </Pie>
                                          <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px' }} itemStyle={{ color: '#c9d1d9' }} />
                                        </PieChart>
                                      </ResponsiveContainer>
                                    </div>
                                 )}

                                 {parsed.bar_chart && parsed.bar_chart.length > 0 && (
                                    <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', height: '220px', minWidth: 0 }}>
                                      <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '5px', textAlign: 'center', fontWeight: 'bold' }}>Key Metrics</div>
                                      <ResponsiveContainer width="99%" height={170}>
                                        <BarChart data={parsed.bar_chart}>
                                          <XAxis dataKey="name" stroke="#8b949e" fontSize={11} tickLine={false} axisLine={false} />
                                          <Tooltip cursor={{ fill: '#161b22' }} contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', color: '#c9d1d9' }} />
                                          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                            {parsed.bar_chart.map((entry, index) => (
                                              <Cell key={`cell-${index}`} fill={entry.fill || '#58a6ff'} />
                                            ))}
                                          </Bar>
                                        </BarChart>
                                      </ResponsiveContainer>
                                    </div>
                                 )}
                               </div>
                               
                               <div style={{ fontSize: '13px', color: '#c9d1d9', lineHeight: '1.6', background: '#0d1117', padding: '18px', borderRadius: '8px', border: '1px solid #30363d' }}>
                                 {parsed.detailed_analysis || parsed.summary}
                               </div>
                             </div>
                           );
                         })()}
                       </>
                    ) : fundData && fundData.error ? (
                        <div style={{ color: '#f85149', fontSize: 13, padding: '20px', gridColumn: '1 / -1' }}>{fundData.error}</div>
                    ) : null}
                  </div>
                </>
             ) : (
                <div style={{ color: '#888', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                   Select a stock from your watchlist to view analysis
                </div>
             )}
          </section>

          <section className="right-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: 0, overflowY: 'auto' }}>
            <div style={{ position: 'relative', flexShrink: 0, width: '100%' }}>
              <input 
                type="text" 
                placeholder="Search to add..." 
                style={{ background: '#0d1117', border: '1px solid #30363d', padding: '10px 20px', color: '#fff', borderRadius: '24px', width: '100%', boxSizing: 'border-box' }}
                value={wlSearch}
                onChange={(e) => handleWlSearchChange(e.target.value)}
                onKeyDown={handleWlAdd}
              />
              {wlSuggestions.length > 0 && (
                <div style={{ position: 'absolute', top: '100%', left: 0, width: '100%', background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', marginTop: '4px', zIndex: 10, maxHeight: '200px', overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                  {wlSuggestions.map(sym => (
                    <div 
                      key={sym} 
                      style={{ padding: '8px 16px', cursor: 'pointer', borderBottom: '1px solid #30363d', color: '#c9d1d9' }}
                      onMouseEnter={e => e.currentTarget.style.background = '#21262d'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      onClick={() => handleWlSuggestionClick(sym)}
                    >
                      {sym}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '12px', flexShrink: 0 }}>
               {watchlist.map(item => (
                  <div key={item.symbol} style={{ position: 'relative' }}>
                     <button 
                       style={{ 
                         width: '100%', padding: '16px', background: selectedWlSymbol === item.symbol ? '#238636' : '#161b22', 
                         color: '#fff', border: '1px solid #30363d', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer', transition: '0.2s'
                       }}
                       onClick={() => handleWlSelect(item.symbol)}
                     >
                        {item.symbol}
                     </button>
                     <button 
                       onClick={() => handleWlRemove(item.symbol)}
                       style={{ position: 'absolute', top: -8, right: -8, background: '#ff5f56', color: '#fff', border: 'none', borderRadius: '50%', width: 22, height: 22, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 'bold' }}
                     >×</button>
                  </div>
               ))}
               {watchlist.length === 0 && <div style={{ color: '#888', gridColumn: '1 / -1' }}>Your watchlist is empty. Search to add or auto-add!</div>}
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: 'auto', flexShrink: 0 }}>
               <button className="white-btn" style={{ flex: 1, padding: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#21262d', color: '#fff' }} onClick={handleWlAutoAdd} disabled={isWlAutoAdding}>
                  {isWlAutoAdding ? 'Scanning Nifty 500...' : 'Auto add to watchlist'}
               </button>
               <button 
                  className="white-btn" 
                  style={{ flex: 1, padding: '12px', background: '#1e90ff', border: 'none', color: '#fff' }} 
                  disabled={!selectedWlSymbol || isWlQuantAnalyzing}
                  onClick={handleWlQuantAnalyze}
               >
                  {isWlQuantAnalyzing ? 'Running CFA Analysis...' : 'Run CFA Quant Analysis'}
               </button>
            </div>
          </section>

          <button 
            onClick={() => setIsChatPopupOpen(!isChatPopupOpen)}
            style={{
              position: 'fixed', bottom: '20px', right: '20px', zIndex: 100,
              width: '50px', height: '50px', borderRadius: '25px',
              background: '#238636', color: '#fff', border: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px'
            }}
            title="Ask Stocky AI"
          >
            💬
          </button>

          {isChatPopupOpen && (
            <div className="chat-section" style={{ 
              position: 'fixed', bottom: '80px', right: '20px', zIndex: 100,
              width: '350px', height: '500px', backgroundColor: '#0d1117',
              boxShadow: '0 8px 24px rgba(0,0,0,0.8)', display: 'flex', flexDirection: 'column'
            }}>
              <div className="chat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #30363d', background: '#161b22' }}>
                <h3 style={{ margin: 0, fontSize: '14px', textTransform: 'uppercase', color: '#8b949e', letterSpacing: '1px' }}>Stocky AI</h3>
                <button onClick={() => setIsChatPopupOpen(false)} style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '20px', lineHeight: 1 }}>×</button>
              </div>
              
              <div className="chat-history" style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
                 {chatHistory.map((msg, i) => (
                   <div key={i} className={`chat-msg ${msg.role}`} dangerouslySetInnerHTML={{ __html: msg.text }}></div>
                 ))}
                 {isChatLoading && <div className="chat-msg bot">Thinking...</div>}
                 <div ref={chatEndRef} />
              </div>

              <div className="chat-input-box" style={{ padding: '16px', borderTop: '1px solid #30363d' }}>
                <input 
                  type="text" 
                  placeholder="Ask Stocky anything..." 
                  value={chatInput} 
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendChat()}
                />
                <button onClick={sendChat} className="send-btn">↑</button>
              </div>
            </div>
          )}
        </main>
      )}

      {activeAppTab === 'Analytics' && (
        <main style={{ padding: '30px', display: 'flex', flexDirection: 'column', gap: '30px', width: '100%', boxSizing: 'border-box', overflowY: 'auto', flex: 1 }}>
           <h2 style={{ color: '#fff', margin: 0, borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>Portfolio Analytics (CFA Framework)</h2>
           
           {/* KPI Row (3 columns) */}
           <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              {/* Aggregate Portfolio Quality */}
              <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                 <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '1px', fontWeight: 'bold' }}>Aggregate Portfolio Quality</div>
                 <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#2ea043' }}>
                    {(() => {
                        const holdings = portfolio.holdings || [];
                        if (!holdings.length) return 0;
                        let total = 0, count = 0;
                        holdings.forEach(h => {
                            const fd = holdingFundData[h.instrument];
                            if (fd && fd.technical_score) { total += fd.technical_score; count++; }
                        });
                        return count ? Math.round(total / count) : 0;
                    })()} <span style={{fontSize: '24px', color: '#8b949e'}}>/ 100</span>
                 </div>
                 <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '10px' }}>EQUAL-WEIGHTED FUNDAMENTAL ASSESSMENT</div>
              </div>

              {/* Herfindahl-Hirschman Index (HHI) */}
              <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', textAlign: 'center', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                 <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '1px', fontWeight: 'bold' }}>Concentration Risk (HHI)</div>
                 {(() => {
                        const holdings = portfolio.holdings || [];
                        const totalEq = portfolio.stats?.current || 1;
                        let hhi = 0;
                        holdings.forEach(h => {
                            const val = (h.qty * h.ltp);
                            const w = (val / totalEq) * 100;
                            hhi += (w * w);
                        });
                        
                        let hhiColor = '#3fb950'; // Green
                        if (hhi > 2500) hhiColor = '#f85149'; // Red
                        else if (hhi >= 1500) hhiColor = '#d29922'; // Orange
                        
                        return (
                            <>
                                <div style={{ fontSize: '48px', fontWeight: 'bold', color: hhiColor }}>
                                   {fmt(hhi, 0)}
                                </div>
                                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '10px' }}>
                                   &lt; 1500: DIVERSIFIED &nbsp;|&nbsp; &gt; 2500: HIGHLY CONCENTRATED
                                </div>
                            </>
                        );
                 })()}
              </div>

              {/* Active Share & Capital Efficiency Alerts */}
              <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                 <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '15px', letterSpacing: '1px', fontWeight: 'bold' }}>Active Share Alerts</div>
                 <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', flex: 1 }}>
                     {(() => {
                         const holdings = portfolio.holdings || [];
                         if (!holdings.length) return <div style={{ color: '#8b949e', fontSize: '12px' }}>Insufficient portfolio data.</div>;
                         
                         let alerts = [];
                         const totalEq = portfolio.stats?.current || 1;
                         
                         holdings.forEach(h => {
                             const fd = holdingFundData[h.instrument];
                             if (!fd || !fd.technical_score) return;
                             
                             const val = h.qty * h.ltp;
                             const weight = (val / totalEq) * 100;
                             
                             if (weight > 10 && fd.technical_score < 40) {
                                 alerts.push(
                                    <div key={`trap-${h.instrument}`} style={{ padding: '10px', background: 'rgba(255, 123, 114, 0.05)', borderLeft: '3px solid #ff7b72', color: '#ff7b72', fontSize: '11px' }}>
                                       <strong>⚠️ Value Trap:</strong> {h.instrument} is overweight ({weight.toFixed(1)}%) with low fundamentals ({fd.technical_score}/100).
                                    </div>
                                 );
                             } else if (weight < 3 && fd.technical_score > 75) {
                                 alerts.push(
                                    <div key={`win-${h.instrument}`} style={{ padding: '10px', background: 'rgba(46, 160, 67, 0.05)', borderLeft: '3px solid #2ea043', color: '#2ea043', fontSize: '11px' }}>
                                       <strong>⭐ High Alpha:</strong> {h.instrument} has robust fundamentals ({fd.technical_score}/100) but is underweight ({weight.toFixed(1)}%).
                                    </div>
                                 );
                             }
                         });
                         
                         if (alerts.length === 0) return <div style={{ color: '#3fb950', fontSize: '11px', padding: '10px', background: 'rgba(46, 160, 67, 0.05)', borderLeft: '3px solid #3fb950' }}>✅ Optimal Allocation: No acute misallocation risks detected.</div>;
                         return alerts;
                     })()}
                 </div>
              </div>
           </div>

           {/* Charts Row (2 columns) */}
           <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              {/* Strategic Asset Allocation Donut */}
              <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', height: '350px', display: 'flex', flexDirection: 'column', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                 <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '1px', textAlign: 'center', fontWeight: 'bold' }}>Strategic Asset Allocation</div>
                 <div style={{ flex: 1, minHeight: 0 }}>
                    <ResponsiveContainer width="99%" height="100%">
                      <PieChart>
                         <defs>
                            <linearGradient id="colorEq" x1="0" y1="0" x2="0" y2="1">
                               <stop offset="5%" stopColor="#58a6ff" stopOpacity={1}/>
                               <stop offset="95%" stopColor="#1f6feb" stopOpacity={1}/>
                            </linearGradient>
                            <linearGradient id="colorMf" x1="0" y1="0" x2="0" y2="1">
                               <stop offset="5%" stopColor="#d2a8ff" stopOpacity={1}/>
                               <stop offset="95%" stopColor="#8957e5" stopOpacity={1}/>
                            </linearGradient>
                            <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
                               <stop offset="5%" stopColor="#3fb950" stopOpacity={1}/>
                               <stop offset="95%" stopColor="#2ea043" stopOpacity={1}/>
                            </linearGradient>
                         </defs>
                         <Pie 
                           data={(() => {
                               const holdings = portfolio.holdings || [];
                               let eqTotal = 0, mfTotal = 0;
                               holdings.forEach(h => {
                                   if (h.asset_type === "EQUITY") eqTotal += (h.qty * h.ltp);
                                   else if (h.asset_type === "MUTUAL FUND") mfTotal += (h.qty * h.ltp);
                                   else eqTotal += (h.qty * h.ltp); // fallback
                               });
                               return [
                                 { name: 'Equities', value: eqTotal, fill: 'url(#colorEq)' },
                                 { name: 'Mutual Funds', value: mfTotal, fill: 'url(#colorMf)' },
                                 { name: 'Cash Equivalents', value: portfolio.stats?.balance || 0, fill: 'url(#colorCash)' }
                               ].filter(d => d.value > 0);
                           })()} 
                           cx="50%" cy="50%" innerRadius={70} outerRadius={110} dataKey="value" stroke="#0d1117" strokeWidth={2}
                         >
                         </Pie>
                         <Tooltip 
                            cursor={{ fill: 'rgba(255,255,255,0.02)' }} 
                            contentStyle={{ background: 'rgba(13, 17, 23, 0.9)', backdropFilter: 'blur(5px)', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: '12px' }} 
                            itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                            formatter={(val) => `₹${fmt(val)}`} 
                         />
                      </PieChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              {/* Top 5 Holdings Bar Chart */}
              <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', height: '350px', display: 'flex', flexDirection: 'column', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                 <div style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '1px', textAlign: 'center', fontWeight: 'bold' }}>Top 5 Capital Allocations (%)</div>
                 <div style={{ flex: 1, minHeight: 0 }}>
                    <ResponsiveContainer width="99%" height="100%">
                      <BarChart data={(() => {
                          const holdings = portfolio.holdings || [];
                          const totalEq = portfolio.stats?.current || 1;
                          let top = holdings.map(h => ({
                              name: h.instrument,
                              value: parseFloat(((h.qty * h.ltp) / totalEq * 100).toFixed(2)),
                          }));
                          top.sort((a, b) => b.value - a.value);
                          return top.slice(0, 5);
                      })()} layout="vertical" margin={{ top: 15, right: 30, left: 50, bottom: 5 }}>
                        <defs>
                            <linearGradient id="barColor" x1="0" y1="0" x2="1" y2="0">
                               <stop offset="0%" stopColor="#1f6feb" stopOpacity={0.8}/>
                               <stop offset="100%" stopColor="#58a6ff" stopOpacity={1}/>
                            </linearGradient>
                        </defs>
                        <XAxis type="number" stroke="#8b949e" fontSize={10} tickLine={false} axisLine={{ stroke: '#30363d' }} />
                        <YAxis dataKey="name" type="category" stroke="#c9d1d9" fontSize={11} tickLine={false} axisLine={{ stroke: '#30363d' }} />
                        <Tooltip 
                            cursor={{ fill: 'rgba(255,255,255,0.02)' }} 
                            contentStyle={{ background: 'rgba(13, 17, 23, 0.9)', backdropFilter: 'blur(5px)', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: '12px' }} 
                            itemStyle={{ color: '#58a6ff', fontWeight: 'bold' }}
                            formatter={(val) => `${val}%`} 
                        />
                        <Bar dataKey="value" fill="url(#barColor)" radius={[0, 4, 4, 0]} barSize={20} />
                      </BarChart>
                    </ResponsiveContainer>
                 </div>
              </div>
           </div>

           {/* AI Portfolio Optimization Panel */}
           <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)', marginTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                 <div style={{ color: '#c9d1d9', fontSize: '16px', fontWeight: 'bold' }}>🧠 Generative AI Portfolio Optimization</div>
                 <button 
                    onClick={handlePortfolioOptimization}
                    disabled={isOptGenerating}
                    style={{ background: '#1f6feb', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: isOptGenerating ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '12px', opacity: isOptGenerating ? 0.7 : 1 }}
                 >
                    {isOptGenerating ? 'Generating CFA Report...' : 'Run Optimization'}
                 </button>
              </div>

              {isOptGenerating && (
                 <div style={{ marginBottom: '20px' }}>
                    <div style={{ color: '#8b949e', fontSize: '12px', marginBottom: '8px', textAlign: 'center' }}>CFA AI Engine is actively processing your portfolio... (Takes ~10 seconds)</div>
                    <div style={{ width: '100%', height: '6px', background: '#30363d', borderRadius: '3px', overflow: 'hidden' }}>
                       <div style={{ width: '50%', height: '100%', background: '#58a6ff', animation: 'progress-anim 2s infinite ease-in-out' }}></div>
                    </div>
                    <style>{`
                       @keyframes progress-anim {
                          0% { transform: translateX(-100%); width: 50%; }
                          100% { transform: translateX(200%); width: 50%; }
                       }
                    `}</style>
                 </div>
              )}

              {optReport && !isOptGenerating && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      <div style={{ color: '#8b949e', fontSize: '14px', lineHeight: '1.6' }}>
                          <ReactMarkdown>{optReport.detailed_analysis}</ReactMarkdown>
                      </div>
                      
                      {/* KPIs */}
                      <div style={{ display: 'flex', gap: '15px', overflowX: 'auto', paddingBottom: '10px' }}>
                          {(optReport.kpis || []).map((k, i) => (
                              <div key={i} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', minWidth: '150px', textAlign: 'center' }}>
                                  <div style={{ color: '#8b949e', fontSize: '11px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 'bold' }}>{k.label}</div>
                                  <div style={{ color: k.color, fontSize: '20px', fontWeight: 'bold' }}>{k.value}</div>
                              </div>
                          ))}
                      </div>

                      {/* Charts */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', height: '250px', display: 'flex', flexDirection: 'column' }}>
                             <div style={{ color: '#8b949e', fontSize: '11px', textTransform: 'uppercase', textAlign: 'center', marginBottom: '10px', fontWeight: 'bold' }}>Risk Profile</div>
                             <div style={{ flex: 1, minHeight: 0 }}>
                                <ResponsiveContainer width="99%" height="100%">
                                  <PieChart>
                                    <Pie data={optReport.doughnut_chart || []} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" stroke="#161b22" strokeWidth={2}>
                                      {(optReport.doughnut_chart || []).map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                                    </Pie>
                                    <Tooltip contentStyle={{ background: 'rgba(13, 17, 23, 0.9)', backdropFilter: 'blur(5px)', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9' }} itemStyle={{ color: '#fff', fontWeight: 'bold' }} formatter={(val) => `${val}%`} />
                                  </PieChart>
                                </ResponsiveContainer>
                             </div>
                          </div>
                          
                          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', height: '250px', display: 'flex', flexDirection: 'column' }}>
                             <div style={{ color: '#8b949e', fontSize: '11px', textTransform: 'uppercase', textAlign: 'center', marginBottom: '10px', fontWeight: 'bold' }}>Suggested Rebalancing Targets (%)</div>
                             <div style={{ flex: 1, minHeight: 0 }}>
                                <ResponsiveContainer width="99%" height="100%">
                                  <BarChart data={optReport.bar_chart || []} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                                    <XAxis type="number" stroke="#8b949e" fontSize={10} tickLine={false} axisLine={{ stroke: '#30363d' }} />
                                    <YAxis dataKey="name" type="category" stroke="#c9d1d9" fontSize={10} tickLine={false} axisLine={{ stroke: '#30363d' }} />
                                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ background: 'rgba(13, 17, 23, 0.9)', backdropFilter: 'blur(5px)', border: '1px solid #30363d', borderRadius: '6px', color: '#c9d1d9' }} itemStyle={{ color: '#58a6ff', fontWeight: 'bold' }} formatter={(val) => `${val}%`} />
                                    <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={15}>
                                      {(optReport.bar_chart || []).map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                                    </Bar>
                                  </BarChart>
                                </ResponsiveContainer>
                             </div>
                          </div>
                      </div>
                  </div>
              )}
           </div>

        </main>
      )}
    </div>
  );
}
