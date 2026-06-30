import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Briefcase, BarChart3, Database, Activity, LayoutDashboard, Layers, TrendingUp, Search, ArrowUpDown, IndianRupee, RefreshCw, Menu, X } from 'lucide-react';
import './index.css';
const rawApiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
let API_BASE = rawApiBase.replace(/\/+$/, '');
if (!API_BASE.endsWith('/api')) {
  API_BASE += '/api';
}

function App() {
  const [activeTab, setActiveTab] = useState('portfolio'); // 'portfolio' | 'trades' | 'stocks'
  const [funds, setFunds] = useState([]);
  const [selectedFund, setSelectedFund] = useState(null);
  const [portfolio, setPortfolio] = useState([]);
  const [trades, setTrades] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  // Mobile sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(prev => !prev);
  const closeSidebar = () => setSidebarOpen(false);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedAndFilteredData = (data, searchKeys) => {
    let filteredData = [...data];
    if (searchQuery) {
      const lowerQuery = searchQuery.toLowerCase();
      filteredData = filteredData.filter(item => 
        searchKeys.some(key => {
          const val = item[key];
          return val && String(val).toLowerCase().includes(lowerQuery);
        })
      );
    }
    
    if (sortConfig.key) {
      filteredData.sort((a, b) => {
        let valA = a[sortConfig.key];
        let valB = b[sortConfig.key];
        if (valA === null || valA === undefined) valA = '';
        if (valB === null || valB === undefined) valB = '';
        
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    
    return filteredData;
  };

  // Fetch funds on mount
  useEffect(() => {
    axios.get(`${API_BASE}/funds`)
      .then(res => {
        setFunds(res.data);
        if (res.data.length > 0) {
          setSelectedFund(res.data[0]);
        }
      })
      .catch(err => {
        console.error("Failed to load funds", err);
        setError("Failed to connect to backend API. Ensure FastAPI is running on port 8000.");
      });
  }, []);

  // Fetch portfolio when selected fund changes
  useEffect(() => {
    if (activeTab === 'portfolio' && selectedFund) {
      setLoading(true);
      setError(null);
      axios.get(`${API_BASE}/portfolio/${selectedFund.fund_id}`)
        .then(res => {
          setPortfolio(res.data);
          setLoading(false);
        })
        .catch(err => {
          if (err.response && err.response.status === 404) {
            setPortfolio([]);
            setError("No baseline data found for this fund.");
          } else {
            setError("Failed to fetch portfolio data.");
          }
          setLoading(false);
        });
    }
  }, [selectedFund, activeTab]);

  // Fetch trades when tab changes to trades
  useEffect(() => {
    if (activeTab === 'trades') {
      setLoading(true);
      axios.get(`${API_BASE}/trades?limit=50`)
        .then(res => {
          setTrades(res.data);
          setLoading(false);
        })
        .catch(err => {
          setError("Failed to fetch trade ledger.");
          setLoading(false);
        });
    }
  }, [activeTab]);

  // Fetch stocks when tab changes to stocks
  useEffect(() => {
    if (activeTab === 'stocks') {
      setLoading(true);
      axios.get(`${API_BASE}/stocks`)
        .then(res => {
          setStocks(res.data);
          setLoading(false);
        })
        .catch(err => {
          setError("Failed to fetch market data.");
          setLoading(false);
        });
    }
  }, [activeTab]);

  // Close sidebar when tab/fund changes on mobile
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    closeSidebar();
  };

  const handleFundSelect = (fund) => {
    setSelectedFund(fund);
    closeSidebar();
  };

  // Summary Metrics
  const activeHoldings = portfolio.filter(p => p.status === 'HELD' || p.status === 'NEW').length;
  const totalBuys = portfolio.reduce((acc, curr) => acc + (curr.total_buys || 0), 0);
  const totalSells = portfolio.reduce((acc, curr) => acc + (curr.total_sells || 0), 0);

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat('en-IN').format(num);
  };

  const formatPrice = (num) => {
    if (num === null || num === undefined) return '-';
    return '₹' + new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  };

  const formatMarketCap = (num) => {
    if (num === null || num === undefined) return '-';
    if (num >= 1e12) return '₹' + (num / 1e12).toFixed(2) + ' T';
    if (num >= 1e7) return '₹' + (num / 1e7).toFixed(2) + ' Cr';
    if (num >= 1e5) return '₹' + (num / 1e5).toFixed(2) + ' L';
    return '₹' + new Intl.NumberFormat('en-IN').format(num);
  };

  const handleTriggerScraper = async () => {
    try {
      alert("Triggering scraper in background... This may take a few minutes.");
      const res = await axios.post(`${API_BASE}/trigger/delta-engine`);
      alert(res.data.message || "Scraper triggered successfully!");
    } catch (err) {
      alert("Error: " + (err.response?.data?.detail || err.message));
    }
  };

  // Sortable table header component
  const SortTh = ({ sortKey, children }) => (
    <th onClick={() => handleSort(sortKey)} style={{ cursor: 'pointer' }}>
      {children} <ArrowUpDown size={14} style={{ display: 'inline', marginLeft: '4px', opacity: 0.5 }} />
    </th>
  );

  return (
    <div className="app-container">
      {/* Mobile Hamburger */}
      <button className="mobile-menu-btn" onClick={toggleSidebar} aria-label="Toggle menu">
        {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Mobile Overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={closeSidebar}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand">
          <Activity size={28} color="#818cf8" />
          AIF Pulse
        </div>

        <div className="nav-section">
          <div className="nav-title">Views</div>
          <button 
            className={`nav-item ${activeTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => handleTabChange('portfolio')}
          >
            <LayoutDashboard size={18} />
            Fund Dashboard
          </button>
          <button 
            className={`nav-item ${activeTab === 'trades' ? 'active' : ''}`}
            onClick={() => handleTabChange('trades')}
          >
            <Layers size={18} />
            Trade Ledger
          </button>
          <button 
            className={`nav-item ${activeTab === 'stocks' ? 'active' : ''}`}
            onClick={() => handleTabChange('stocks')}
          >
            <BarChart3 size={18} />
            Market View
          </button>
        </div>

        {activeTab === 'portfolio' && (
          <div className="nav-section" style={{ flex: 1, overflowY: 'auto' }}>
            <div className="nav-title">Select Fund</div>
            {funds.map(fund => (
              <button 
                key={fund.fund_id}
                className={`nav-item ${selectedFund?.fund_id === fund.fund_id ? 'active' : ''}`}
                onClick={() => handleFundSelect(fund)}
                style={{ fontSize: '0.85rem' }}
              >
                <Database size={16} />
                {fund.fund_name}
              </button>
            ))}
          </div>
        )}
        
        <div className="sidebar-action">
          <button className="scraper-btn" onClick={handleTriggerScraper}>
            <RefreshCw size={16} />
            Run Scraper
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {error && !loading && (
          <div className="glass-panel" style={{ borderLeft: '4px solid var(--danger)', marginBottom: '2rem' }}>
            <h4 style={{ color: 'var(--danger)' }}>Notice</h4>
            <p style={{ color: 'var(--text-muted)' }}>{error}</p>
          </div>
        )}

        {/* --- PORTFOLIO VIEW --- */}
        {activeTab === 'portfolio' && selectedFund && (
          <>
            <div className="topbar">
              <div>
                <h1 className="page-title">{selectedFund.fund_name}</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  {selectedFund.regulatory_type} • Baseline Source: {selectedFund.amc_scheme_name || 'Trendlyne'}
                </p>
              </div>
              <div className="search-container">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  placeholder="Search stocks..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="metrics-grid">
              <div className="glass-panel metric-card">
                <div className="metric-label">Active Holdings</div>
                <div className="metric-value">{activeHoldings}</div>
              </div>
              <div className="glass-panel metric-card">
                <div className="metric-label">Total Volume (Buys)</div>
                <div className="metric-value" style={{ color: 'var(--secondary)' }}>{formatNumber(totalBuys)}</div>
              </div>
              <div className="glass-panel metric-card">
                <div className="metric-label">Total Volume (Sells)</div>
                <div className="metric-value" style={{ color: 'var(--danger)' }}>{formatNumber(totalSells)}</div>
              </div>
            </div>

            <div className="glass-panel">
              <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Briefcase size={20} />
                Reconstructed Portfolio
              </h3>
              
              {loading ? (
                <div className="loader"></div>
              ) : portfolio.length === 0 ? (
                <div className="empty-state">
                  <Database className="empty-icon" />
                  <p>No baseline data available for this fund.</p>
                  <p style={{ fontSize: '0.875rem' }}>Run the python scrapers to populate the database.</p>
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <SortTh sortKey="stock_name">Stock Name</SortTh>
                        <SortTh sortKey="current_price">CMP</SortTh>
                        <SortTh sortKey="market_cap">Market Cap</SortTh>
                        <SortTh sortKey="baseline_qty">Baseline Qty</SortTh>
                        <SortTh sortKey="total_buys">Buy Qty</SortTh>
                        <SortTh sortKey="total_sells">Sell Qty</SortTh>
                        <SortTh sortKey="current_qty">Current Qty</SortTh>
                        <SortTh sortKey="net_delta">Net Delta</SortTh>
                        <SortTh sortKey="status">Status</SortTh>
                      </tr>
                    </thead>
                    <tbody>
                      {getSortedAndFilteredData(portfolio, ['stock_name']).map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 500 }}>{row.stock_name}</td>
                          <td style={{ color: 'var(--accent)', fontWeight: 500 }}>{formatPrice(row.current_price)}</td>
                          <td style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{formatMarketCap(row.market_cap)}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{formatNumber(row.baseline_qty)}</td>
                          <td style={{ color: 'var(--secondary)' }}>{formatNumber(row.total_buys)}</td>
                          <td style={{ color: 'var(--danger)' }}>{formatNumber(row.total_sells)}</td>
                          <td style={{ fontSize: '1.1rem' }}>{formatNumber(row.current_qty)}</td>
                          <td>
                            <span style={{ 
                              color: row.net_delta > 0 ? 'var(--secondary)' : row.net_delta < 0 ? 'var(--danger)' : 'var(--text-muted)',
                              display: 'flex', alignItems: 'center', gap: '0.25rem'
                            }}>
                              {row.net_delta > 0 && '+'}{formatNumber(row.net_delta)}
                            </span>
                          </td>
                          <td>
                            <span className={`badge badge-${(row.status || '').toLowerCase()}`}>
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {/* --- TRADES VIEW --- */}
        {activeTab === 'trades' && (
           <>
             <div className="topbar">
               <div>
                 <h1 className="page-title">Trade Ledger</h1>
                 <p style={{ color: 'var(--text-muted)' }}>Recent Bulk & Block Deals via Delta Engine</p>
               </div>
             </div>
             
             <div className="glass-panel">
               <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <TrendingUp size={20} />
                 Recent Intercepted Deals
               </h3>

               {loading ? (
                <div className="loader"></div>
               ) : trades.length === 0 ? (
                <div className="empty-state">
                  <BarChart3 className="empty-icon" />
                  <p>No trades recorded in the ledger.</p>
                  <p style={{ fontSize: '0.875rem' }}>Run `python main.py scrape-deals` during market hours.</p>
                </div>
               ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Fund</th>
                        <th>Stock</th>
                        <th>Type</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Exchange</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((trade) => (
                        <tr key={trade.id}>
                          <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{trade.trade_date}</td>
                          <td style={{ fontWeight: 500 }}>{funds.find(f => f.fund_id === trade.fund_id)?.fund_name || trade.fund_id}</td>
                          <td>{trade.stock_name || trade.symbol}</td>
                          <td>
                            <span className={`badge badge-${trade.transaction_type.toLowerCase()}`}>
                              {trade.transaction_type}
                            </span>
                          </td>
                          <td>{formatNumber(trade.quantity)}</td>
                          <td>{formatPrice(trade.execution_price)}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{trade.exchange} ({trade.deal_type})</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
               )}
             </div>
           </>
        )}

        {/* --- STOCKS VIEW --- */}
        {activeTab === 'stocks' && (
           <>
             <div className="topbar">
               <div>
                 <h1 className="page-title">Market View</h1>
                 <p style={{ color: 'var(--text-muted)' }}>Complete list of all stocks held by each tracked fund</p>
               </div>
               <div className="search-container">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  placeholder="Search funds or stocks..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
               </div>
             </div>
             
             <div className="glass-panel">
               <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <TrendingUp size={20} />
                 All Tracked Stocks
               </h3>

               {loading ? (
                <div className="loader"></div>
               ) : stocks.length === 0 ? (
                <div className="empty-state">
                  <Database className="empty-icon" />
                  <p>No stock data available.</p>
                </div>
               ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <SortTh sortKey="fund_name">Fund Name</SortTh>
                        <SortTh sortKey="stock_name">Stock Name</SortTh>
                        <SortTh sortKey="current_price">CMP</SortTh>
                        <SortTh sortKey="market_cap">Market Cap</SortTh>
                        <SortTh sortKey="baseline_qty">Baseline Qty</SortTh>
                        <SortTh sortKey="total_buys">Buy Qty</SortTh>
                        <SortTh sortKey="total_sells">Sell Qty</SortTh>
                        <SortTh sortKey="current_qty">Current Qty</SortTh>
                        <SortTh sortKey="net_delta">Net Delta</SortTh>
                      </tr>
                    </thead>
                    <tbody>
                      {getSortedAndFilteredData(stocks, ['fund_name', 'stock_name']).map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 500, color: 'var(--text-muted)' }}>{row.fund_name}</td>
                          <td style={{ fontWeight: 500 }}>{row.stock_name}</td>
                          <td style={{ color: 'var(--accent)', fontWeight: 500 }}>{formatPrice(row.current_price)}</td>
                          <td style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{formatMarketCap(row.market_cap)}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{formatNumber(row.baseline_qty)}</td>
                          <td style={{ color: 'var(--secondary)' }}>{formatNumber(row.total_buys)}</td>
                          <td style={{ color: 'var(--danger)' }}>{formatNumber(row.total_sells)}</td>
                          <td style={{ fontSize: '1.1rem' }}>{formatNumber(row.current_qty)}</td>
                          <td>
                            <span style={{ 
                              color: row.net_delta > 0 ? 'var(--secondary)' : row.net_delta < 0 ? 'var(--danger)' : 'var(--text-muted)',
                              display: 'flex', alignItems: 'center', gap: '0.25rem'
                            }}>
                              {row.net_delta > 0 && '+'}{formatNumber(row.net_delta)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
               )}
             </div>
           </>
        )}
      </main>
    </div>
  );
}

export default App;
