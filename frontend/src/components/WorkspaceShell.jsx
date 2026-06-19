import { useEffect, useState } from 'react';
import { Activity, Cpu, FileText, Moon, Shield, Sun } from 'lucide-react';
import { fetchHealthStatus } from '../services/apiService';

export default function WorkspaceShell({ activeSection, setActiveSection, children }) {
  const [apiStatus, setApiStatus] = useState('checking'); // 'ok' | 'degraded' | 'offline' | 'checking'
  const [apiVersion, setApiVersion] = useState('...');
  const [theme, setTheme] = useState(() => localStorage.getItem('aleph-theme') || 'light');

  useEffect(() => {
    const check = async () => {
      const result = await fetchHealthStatus();
      setApiStatus(result.status || 'offline');
      setApiVersion(result.version || '?');
    };
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    localStorage.setItem('aleph-theme', theme);
    document.documentElement.dataset.alephTheme = theme;
  }, [theme]);

  const statusConfig = {
    ok:       { dot: 'bg-[#99B29B]', ping: 'bg-[#99B29B]', label: 'Pipeline Connected',   text: 'text-[#6B6864]' },
    degraded: { dot: 'bg-amber-400',  ping: 'bg-amber-400',  label: 'Pipeline Degraded',    text: 'text-amber-600' },
    offline:  { dot: 'bg-red-400',    ping: 'bg-red-400',    label: 'Backend Offline',       text: 'text-red-500'  },
    checking: { dot: 'bg-[#D6C8B5]', ping: 'bg-[#D6C8B5]', label: 'Connecting...',         text: 'text-[#6B6864]' },
  };

  const st = statusConfig[apiStatus] ?? statusConfig.checking;

  const navItems = [
    { id: 'topology',      label: 'Graph Topology',    icon: Shield   },
    { id: 'typology',      label: 'Typology Alerts',   icon: Activity },
    { id: 'ml-explain',    label: 'Explainability Hub',icon: Cpu      },
    { id: 'str-alignment', label: 'STR Verification',  icon: FileText },
  ];

  return (
    <div className="aleph-shell min-h-screen bg-[#FAF7F2] text-[#2D2D2D] flex overflow-hidden font-sans" data-theme={theme}>

      {/* Sidebar */}
      <aside className="w-76 bg-white border-r border-[#EAE1D4] flex flex-col justify-between shrink-0">
        <div className="p-8">
          {/* Brand */}
          <div className="mb-12">
            <div className="flex items-center space-x-2.5">
              <span className="w-3.5 h-3.5 bg-[#99B29B] rounded-sm transform rotate-45 shadow-sm" />
              <h2 className="text-xl font-serif font-bold tracking-tight text-[#2D2D2D]">ALEPH</h2>
            </div>
            <p className="text-[9px] uppercase tracking-[0.2em] text-[#6B6864] font-bold mt-2">
              AML Intelligence Platform
            </p>
          </div>

          {/* Navigation */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center space-x-3.5 px-4 py-3 rounded-lg text-xs font-semibold
                    tracking-wider uppercase transition-all duration-200 hover:translate-x-1.5 ${
                    isActive
                      ? 'bg-[#99B29B] text-white shadow-sm hover:translate-x-0'
                      : 'text-[#6B6864] hover:bg-[#FAF7F2] hover:text-[#2D2D2D]'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                  {isActive && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white opacity-70" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Live Connection Status */}
        <div className="p-8 border-t border-[#EAE1D4] bg-[#FAF7F2]/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <span className="relative flex h-2 w-2">
                {(apiStatus === 'ok' || apiStatus === 'checking') && (
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${st.ping} opacity-75`} />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${st.dot}`} />
              </span>
              <span className={`text-[10px] font-bold uppercase tracking-wider ${st.text}`}>
                {st.label}
              </span>
            </div>
            <span className="text-[10px] text-[#C07A50] font-mono font-bold">
              v{apiVersion}
            </span>
          </div>
          {apiStatus === 'offline' && (
            <p className="text-[9px] text-red-400 mt-2 font-mono">
              Check: uvicorn app.main:app --port 8000
            </p>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-[#EAE1D4] flex items-center justify-between px-10 shrink-0">
          <div className="flex items-center space-x-3">
            {/* Subtle left accent bar */}
            <span className="h-5 w-0.5 rounded-full bg-[#99B29B]" />
            <span className="text-xs font-bold uppercase tracking-widest text-[#6B6864]">
              Active Layer:{' '}
              <span className="text-[#2D2D2D] ml-1">
                {navItems.find(n => n.id === activeSection)?.label ?? activeSection}
              </span>
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
              className="aleph-theme-toggle"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            >
              <span className="aleph-theme-toggle__icon">
                {theme === 'light' ? <Sun size={15} /> : <Moon size={15} />}
              </span>
              <span>{theme}</span>
            </button>
            <div className="text-right">
              <p className="text-[10px] text-[#6B6864] font-medium uppercase tracking-wider">
                Analyst Session
              </p>
              <p className="text-xs font-bold text-[#2D2D2D]">AML.DIR_NEPAL</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-[#EAE1D4] flex items-center justify-center font-bold text-xs text-[#6B6864]">
              AN
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-10">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
