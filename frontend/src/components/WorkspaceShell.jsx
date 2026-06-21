import { useEffect, useState } from 'react';
import { Activity, Cpu, FileText, Moon, Shield, Sun, Menu, X } from 'lucide-react';
import { fetchHealthStatus } from '../services/apiService';

export default function WorkspaceShell({ activeSection, setActiveSection, children }) {
  const [apiStatus, setApiStatus] = useState('checking'); // 'ok' | 'degraded' | 'offline' | 'checking'
  const [apiVersion, setApiVersion] = useState('...');
  const [theme, setTheme] = useState(() => localStorage.getItem('aleph-theme') || 'light');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

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

  const navItems = [
    { id: 'topology', label: 'Graph Topology', icon: Shield },
    { id: 'typology', label: 'Typology Alerts', icon: Activity },
    { id: 'ml-explain', label: 'Explainability Hub', icon: Cpu },
    { id: 'str-alignment', label: 'STR Verification', icon: FileText },
  ];

  return (
    <div className="aleph-shell min-h-screen bg-[#FAF7F2] text-[#2D2D2D] flex overflow-hidden font-sans" data-theme={theme}>

      {/* Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-[#2D2D2D]/20 backdrop-blur-[2px] z-40 transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 w-76 bg-white border-r border-[#EAE1D4] flex flex-col justify-between shrink-0 z-50 transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-8">
          {/* Brand & Close */}
          <div className="flex items-center justify-between mb-12">
            <div>
              <div className="flex items-center space-x-2.5">
                <span className="w-3.5 h-3.5 bg-[#99B29B] rounded-sm transform rotate-45 shadow-sm" />
                <h2 className="text-xl font-serif font-bold tracking-tight text-[#2D2D2D]">ALEPH</h2>
              </div>
              <p className="text-[9px] uppercase tracking-[0.2em] text-[#6B6864] font-bold mt-2">
                AML Intelligence Platform
              </p>
            </div>
            <button 
              onClick={() => setIsSidebarOpen(false)}
              className="p-2 -mr-2 text-[#6B6864] hover:text-[#2D2D2D] hover:bg-[#FAF7F2] rounded-lg transition-colors"
              aria-label="Close Sidebar"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveSection(item.id);
                    setIsSidebarOpen(false);
                  }}
                  className={`w-full flex items-center space-x-3.5 px-4 py-3 rounded-lg text-xs font-semibold
                    tracking-wider uppercase transition-all duration-200 hover:translate-x-1.5 ${isActive
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
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-[#EAE1D4] flex items-center justify-between px-10 shrink-0 relative z-30">
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="p-1.5 -ml-4 text-[#6B6864] hover:text-[#2D2D2D] hover:bg-[#FAF7F2] rounded-md transition-colors"
              aria-label="Open Sidebar"
            >
              <Menu size={20} />
            </button>
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
              <p className="text-xs font-bold text-[#2D2D2D]">Team_Aleph</p>
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
