import React from 'react';
import { Shield, Cpu, Activity, FileText } from 'lucide-react';

export default function WorkspaceShell({ activeSection, setActiveSection, children }) {
  const navItems = [
    { id: 'topology', label: 'Graph Topology', icon: Shield },
    { id: 'typology', label: 'Typology Alerts', icon: Activity },
    { id: 'ml-explain', label: 'Explainability Hub', icon: Cpu },
    { id: 'str-alignment', label: 'STR Verification', icon: FileText }
  ];

  return (
    <div className="min-h-screen bg-[#FAF7F2] text-[#2D2D2D] flex overflow-hidden font-sans">
      
      {/* Sidebar Navigation */}
      <aside className="w-76 bg-white border-r border-[#EAE1D4] flex flex-col justify-between shrink-0">
        <div className="p-8">
          <div className="mb-12">
            <div className="flex items-center space-x-2">
              <span className="w-3.5 h-3.5 bg-[#99B29B] rounded-sm transform rotate-45" />
              <h2 className="text-xl font-serif font-bold tracking-tight text-[#2D2D2D]">AMLIOS-X</h2>
            </div>
            <p className="text-[9px] uppercase tracking-[0.25em] text-[#6B6864] font-semibold mt-1">
              Track 3 • Graph Intelligence
            </p>
          </div>

          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center space-x-3.5 px-4 py-3 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all duration-200 ${
                    isActive 
                      ? 'bg-[#99B29B] text-white shadow-sm' 
                      : 'text-[#6B6864] hover:bg-[#FAF7F2] hover:text-[#2D2D2D]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* System Health Indicator */}
        <div className="p-8 border-t border-[#EAE1D4] bg-[#FAF7F2]/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#99B29B] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#99B29B]"></span>
              </span>
              <span className="text-[10px] text-[#6B6864] font-bold uppercase tracking-wider">
                Pipeline Connected
              </span>
            </div>
            <span className="text-[10px] text-[#C07A50] font-mono font-bold">v3.1.2</span>
          </div>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-[#EAE1D4] flex items-center justify-between px-10 shrink-0">
          <span className="text-xs font-bold uppercase tracking-widest text-[#6B6864]">
            Active Workspace Layer: <span className="text-[#2D2D2D]">{activeSection}</span>
          </span>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-[10px] text-[#6B6864] font-medium uppercase tracking-wider">Analyst Session</p>
              <p className="text-xs font-bold text-[#2D2D2D]">AML.DIR_NEPAL</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-[#EAE1D4] flex items-center justify-center font-bold text-xs text-[#6B6864]">
              AN
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-10">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
