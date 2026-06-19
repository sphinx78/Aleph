import { useState, useEffect } from 'react';
import WorkspaceShell from './WorkspaceShell';
import DynamicMetricCard from './DynamicMetricCard';
import LayeringAlluvial from './LayeringAlluvial';
import ClaimsVerification from './ClaimsVerification';
import AlephCard from './AlephCard';
import { 
  fetchHighRiskAccounts, 
  fetchAccountFeatures, 
  fetchAccountShap, 
  fetchAccountClaims, 
  fetchAccountTransactions, 
  fetchAccountCopilot, 
  fetchTypologyAlerts 
} from '../services/apiService';

export default function DashboardMain() {
  const [activeSection, setActiveSection] = useState('topology');
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  
  // Specific account data states
  const [features, setFeatures] = useState(null);
  const [shapData, setShapData] = useState([]);
  const [claims, setClaims] = useState([]);
  const [pathData, setPathData] = useState([]);
  const [copilotReport, setCopilotReport] = useState('');
  const [allAlerts, setAllAlerts] = useState([]);
  
  // UI states
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [minScoreFilter, setMinScoreFilter] = useState(0.5);
  const [selectedBands, setSelectedBands] = useState(['CRITICAL', 'SEVERE', 'HIGH']);
  const [copiedCopilot, setCopiedCopilot] = useState(false);

  // Initial load
  useEffect(() => {
    async function initData() {
      try {
        setLoading(true);
        const fetchedAccounts = await fetchHighRiskAccounts();
        setAccounts(fetchedAccounts);
        
        if (fetchedAccounts.length > 0) {
          setSelectedAccountId(String(fetchedAccounts[0].account_id));
        }
        
        const fetchedAlerts = await fetchTypologyAlerts();
        setAllAlerts(fetchedAlerts);
      } catch (err) {
        console.error("Error loading dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    initData();
  }, []);

  // Update selected account deep-dive details
  useEffect(() => {
    if (!selectedAccountId) return;
    
    async function loadAccountDetails() {
      try {
        setLoadingDetails(true);
        
        // Parallel fetching
        const [feat, shap, clms, path, copilot] = await Promise.allSettled([
          fetchAccountFeatures(selectedAccountId),
          fetchAccountShap(selectedAccountId),
          fetchAccountClaims(selectedAccountId),
          fetchAccountTransactions(selectedAccountId),
          fetchAccountCopilot(selectedAccountId)
        ]);

        if (feat.status === 'fulfilled') setFeatures(feat.value);
        if (shap.status === 'fulfilled') setShapData(shap.value);
        if (clms.status === 'fulfilled') setClaims(clms.value);
        if (path.status === 'fulfilled') setPathData(path.value);
        if (copilot.status === 'fulfilled') setCopilotReport(copilot.value);
        
        setCopiedCopilot(false);
      } catch (err) {
        console.error("Error loading account deep dive details:", err);
      } finally {
        setLoadingDetails(false);
      }
    }

    loadAccountDetails();
  }, [selectedAccountId]);

  // Filter accounts
  const filteredAccounts = accounts.filter(acc => {
    const scoreVal = acc.risk_score || 0;
    const bandVal = acc.risk_band || 'LOW';
    return scoreVal >= minScoreFilter && selectedBands.includes(bandVal);
  });

  // Toggle risk bands
  const toggleBand = (band) => {
    if (selectedBands.includes(band)) {
      setSelectedBands(selectedBands.filter(b => b !== band));
    } else {
      setSelectedBands([...selectedBands, band]);
    }
  };

  const handleDownloadReport = () => {
    if (!copilotReport) return;
    const element = document.createElement("a");
    const file = new Blob([copilotReport], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = `SAR_Report_Account_${selectedAccountId}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const copyToClipboard = () => {
    if (!copilotReport) return;
    navigator.clipboard.writeText(copilotReport);
    setCopiedCopilot(true);
    setTimeout(() => setCopiedCopilot(false), 2000);
  };

  // Helper values
  const totalScored = accounts.length;
  const criticalCount = accounts.filter(a => a.risk_band === 'CRITICAL').length;
  const maxRisk = accounts.length > 0 ? Math.max(...accounts.map(a => a.risk_score || 0)) : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex flex-col justify-center items-center font-sans">
        <div className="relative flex items-center justify-center mb-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#99B29B]"></div>
          <span className="absolute w-3.5 h-3.5 bg-[#C07A50] rounded-sm transform rotate-45 animate-pulse" />
        </div>
        <p className="text-xs uppercase tracking-widest text-[#6B6864] font-bold">Loading system state...</p>
      </div>
    );
  }

  return (
    <WorkspaceShell activeSection={activeSection} setActiveSection={setActiveSection}>
      
      {/* Top Overview Cards (Only shown on Graph Topology & Explainability Hub) */}
      {(activeSection === 'topology' || activeSection === 'ml-explain') && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
          
          <DynamicMetricCard
            variant="mint"
            title="Leiden Clustering" 
            uppercaseSub="Community Risk Index" 
            value={features && features.scan_cluster !== undefined ? `Cluster ${features.scan_cluster}` : "High Density"}
            trend={{ direction: 'up', value: '+14% Risk' }}
          >
            Node clusters with low account ages and high internal transaction ratios 
            are grouped into localized risk pools.
          </DynamicMetricCard>

          <DynamicMetricCard
            variant="violet"
            title="Hawkes Intensity" 
            uppercaseSub="Time-Series Velocity" 
            value={features && features.hawkes_intensity !== undefined ? `${features.hawkes_intensity.toFixed(3)} λ` : "8.824 λ"}
          >
            Tracks rapid cash flow patterns across accounts to isolate automated layering cycles.
          </DynamicMetricCard>

          <DynamicMetricCard
            variant="solar"
            title="Structuring Evasion" 
            uppercaseSub="Threshold Proximity" 
            value={features && features.tps_score !== undefined ? `${(features.tps_score * 100).toFixed(1)}%` : "98.0%"}
          >
            Identifies transaction patterns structured just below standard regulatory limits (e.g., NPR 1,000,000).
          </DynamicMetricCard>
        </div>
      )}

      {/* Main Workspace Layers */}
      {activeSection === 'topology' && (
        <div className="space-y-10">
          
          {/* Top Panel: Queue & Profile */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">
            
            {/* Action Queue Control & Table */}
            <AlephCard className="xl:col-span-2 p-8 flex flex-col h-[520px]">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div>
                  <h3 className="text-lg font-serif font-bold text-[#2D2D2D]">High-Risk Analyst Action Queue</h3>
                  <p className="text-xs text-[#6B6864] font-light mt-0.5">Prioritized suspicious entities mapped by graph risk contagion.</p>
                </div>
                
                {/* Score slider & Filters */}
                <div className="flex items-center space-x-6 shrink-0">
                  <div className="flex flex-col">
                    <span className="text-[9px] uppercase tracking-wider text-[#6B6864] font-bold">Min Score: {minScoreFilter.toFixed(2)}</span>
                    <input 
                      type="range" 
                      min="0" 
                      max="1" 
                      step="0.05" 
                      value={minScoreFilter} 
                      onChange={(e) => setMinScoreFilter(parseFloat(e.target.value))}
                      className="w-28 accent-[#99B29B] h-1 bg-[#EAE1D4] rounded-lg cursor-pointer"
                    />
                  </div>
                  <div className="flex space-x-1">
                    {['CRITICAL', 'SEVERE', 'HIGH'].map(b => (
                      <button
                        key={b}
                        onClick={() => toggleBand(b)}
                        className={`px-2 py-0.5 rounded text-[8px] font-bold tracking-wider uppercase transition-all ${
                          selectedBands.includes(b) 
                            ? 'bg-[#99B29B] text-white' 
                            : 'bg-[#FAF7F2] text-[#6B6864] border border-[#EAE1D4]'
                        }`}
                      >
                        {b}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="flex-1 overflow-y-auto border border-[#FAF7F2] rounded-lg">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#FAF7F2] text-[#6B6864] uppercase tracking-wider text-[9px] font-bold sticky top-0 border-b border-[#EAE1D4]">
                      <th className="py-3 px-4">Rank</th>
                      <th className="py-3 px-4">Account ID</th>
                      <th className="py-3 px-4">Risk Score</th>
                      <th className="py-3 px-4">Risk Band</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EAE1D4]">
                    {filteredAccounts.map((acc) => (
                      <tr 
                        key={acc.account_id} 
                        onClick={() => setSelectedAccountId(String(acc.account_id))}
                        className={`hover:bg-[#FAF7F2]/50 cursor-pointer transition-colors ${
                          selectedAccountId === String(acc.account_id) ? 'bg-[#FAF7F2] font-semibold' : ''
                        }`}
                      >
                        <td className="py-3 px-4 text-[#6B6864] font-mono">#{acc.rank || '-'}</td>
                        <td className="py-3 px-4 font-mono">{acc.account_id}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono">{(acc.risk_score || 0).toFixed(3)}</span>
                            <div className="w-16 bg-[#EAE1D4] h-1.5 rounded-full overflow-hidden">
                              <div 
                                className="bg-[#C07A50] h-full rounded-full" 
                                style={{ width: `${(acc.risk_score || 0) * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                            acc.risk_band === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                            acc.risk_band === 'SEVERE' ? 'bg-orange-100 text-orange-700' :
                            acc.risk_band === 'HIGH' ? 'bg-[#C07A50]/15 text-[#C07A50]' : 'bg-[#99B29B]/15 text-[#99B29B]'
                          }`}>
                            {acc.risk_band}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button 
                            className="text-[#99B29B] hover:text-[#5F7F62] font-bold tracking-wider uppercase text-[10px]"
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    ))}
                    {filteredAccounts.length === 0 && (
                      <tr>
                        <td colSpan="5" className="py-10 text-center text-[#6B6864] italic">
                          No entities match the filtered criteria.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </AlephCard>

            {/* Entity Deep-Dive Panel */}
            <AlephCard className="p-8 h-[520px] flex flex-col justify-between">
              <div>
                <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
                  Deep-Dive Analyst Panel
                </span>
                <h3 className="text-xl font-serif text-[#2D2D2D] font-bold mt-1 mb-6">Entity Risk Profile</h3>

                {loadingDetails ? (
                  <div className="flex flex-col items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-[#99B29B] mb-2"></div>
                    <p className="text-[10px] text-[#6B6864] uppercase tracking-wider">Syncing node features...</p>
                  </div>
                ) : features ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4 border-b border-[#FAF7F2] pb-4">
                      <div>
                        <span className="text-[9px] text-[#6B6864] uppercase tracking-wider font-bold">Account ID</span>
                        <p className="text-sm font-mono font-bold text-[#2D2D2D] mt-0.5">{selectedAccountId}</p>
                      </div>
                      <div>
                        <span className="text-[9px] text-[#6B6864] uppercase tracking-wider font-bold">Risk Classification</span>
                        <p className="text-sm font-bold text-[#C07A50] mt-0.5">
                          {accounts.find(a => String(a.account_id) === selectedAccountId)?.risk_band || 'UNKNOWN'}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3.5 text-xs">
                      <div className="flex justify-between items-center py-0.5">
                        <span className="text-[#6B6864] font-light">PageRank Importance:</span>
                        <code className="font-mono font-semibold bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[11px]">
                          {features.pagerank ? features.pagerank.toFixed(6) : '0.000000'}
                        </code>
                      </div>
                      <div className="flex justify-between items-center py-0.5">
                        <span className="text-[#6B6864] font-light">Hawkes Process Intensity:</span>
                        <code className="font-mono font-semibold bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[11px]">
                          {features.hawkes_intensity ? features.hawkes_intensity.toFixed(4) : '0.0000'}
                        </code>
                      </div>
                      <div className="flex justify-between items-center py-0.5">
                        <span className="text-[#6B6864] font-light">Directed Flow Asymmetry (DFA):</span>
                        <code className="font-mono font-semibold bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[11px]">
                          {features.dfa_score ? features.dfa_score.toFixed(3) : '0.000'}
                        </code>
                      </div>
                      <div className="flex justify-between items-center py-0.5">
                        <span className="text-[#6B6864] font-light">Threshold Proximity (TPS):</span>
                        <code className="font-mono font-semibold bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[11px]">
                          {features.tps_score ? `${(features.tps_score * 100).toFixed(1)}%` : '0.0%'}
                        </code>
                      </div>
                      <div className="flex justify-between items-center py-0.5">
                        <span className="text-[#6B6864] font-light">Burt's Constraint (Structural Hole):</span>
                        <code className="font-mono font-semibold bg-[#FAF7F2] px-1.5 py-0.5 rounded text-[11px]">
                          {features.structural_constraint ? features.structural_constraint.toFixed(4) : '1.0000'}
                        </code>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-[#6B6864] italic">Select an account from the action queue to view profile.</p>
                )}
              </div>

              <div className="pt-6 border-t border-[#EAE1D4] flex items-center justify-between text-[10px] text-[#6B6864]">
                <span>Scored Entities: <strong>{totalScored}</strong></span>
                <span>Max Risk: <strong>{maxRisk.toFixed(3)}</strong></span>
                <span>Critical alerts: <strong className="text-red-600">{criticalCount}</strong></span>
              </div>
            </AlephCard>

          </div>

          {/* Lower Alluvial Path & Claims */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">
            <div className="xl:col-span-2">
              <LayeringAlluvial pathData={pathData} />
            </div>
            <div>
              <ClaimsVerification claimsList={claims} />
            </div>
          </div>

        </div>
      )}

      {/* Typology Alerts Layer */}
      {activeSection === 'typology' && (
        <AlephCard className="p-8">
          <div className="mb-6">
            <h3 className="text-xl font-serif font-bold text-[#2D2D2D]">Flagged Typology Alerts Registry</h3>
            <p className="text-xs text-[#6B6864] font-light mt-0.5">Identified suspicious behaviors matching rule-based templates.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#FAF7F2] text-[#6B6864] uppercase tracking-wider text-[9px] font-bold border-b border-[#EAE1D4]">
                  <th className="py-3 px-4">Account ID</th>
                  <th className="py-3 px-4">Typology Rule</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Analysis / Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EAE1D4]">
                {allAlerts.map((alt, idx) => (
                  <tr 
                    key={idx} 
                    onClick={() => {
                      setSelectedAccountId(String(alt.account_id));
                      setActiveSection('topology');
                    }}
                    className="hover:bg-[#FAF7F2]/50 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold">{alt.account_id}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded bg-[#C07A50]/15 text-[#C07A50] font-bold text-[10px] tracking-wide uppercase">
                        {alt.typology}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      {alt.confidence !== undefined ? `${(alt.confidence * 100).toFixed(0)}%` : '90%'}
                    </td>
                    <td className="py-3.5 px-4 text-[#6B6864] font-light">{alt.details}</td>
                  </tr>
                ))}
                {allAlerts.length === 0 && (
                  <tr>
                    <td colSpan="4" className="py-10 text-center text-[#6B6864] italic">No typology alerts logged.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </AlephCard>
      )}

      {/* Explainability Hub */}
      {activeSection === 'ml-explain' && (
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-10">
          
          {/* SHAP Attributions (Left 2 columns) */}
          <AlephCard className="xl:col-span-2 p-8 flex flex-col h-[560px]">
            <div className="mb-6">
              <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">Explainable Machine Learning</span>
              <h3 className="text-xl font-serif font-bold text-[#2D2D2D] mt-0.5">SHAP Feature Attributions</h3>
              <p className="text-xs text-[#6B6864] font-light mt-0.5">Showing feature impact on risk score for Account {selectedAccountId}.</p>
            </div>

            {loadingDetails ? (
              <div className="flex-1 flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-[#99B29B] mb-2"></div>
                <p className="text-[10px] text-[#6B6864] uppercase tracking-wider">Loading attributions...</p>
              </div>
            ) : shapData.length > 0 ? (
              <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                {shapData.map((shap, index) => {
                  const val = shap.shap_value || 0;
                  const isPositive = val >= 0;
                  const absPercent = Math.min(Math.abs(val) * 300, 100); // scale factor for visual visibility
                  return (
                    <div key={index} className="space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-mono font-medium text-[#2D2D2D]">{shap.feature}</span>
                        <div className="flex items-center space-x-2">
                          <span className={`text-[9px] uppercase tracking-widest font-bold px-1.5 py-0.2 rounded ${
                            shap.driver_group === 'community' ? 'bg-[#99B29B]/15 text-[#99B29B]' :
                            shap.driver_group === 'counterparty' ? 'bg-[#C07A50]/15 text-[#C07A50]' : 'bg-[#FAF7F2] text-[#6B6864]'
                          }`}>
                            {shap.driver_group}
                          </span>
                          <span className={`font-mono font-semibold ${isPositive ? 'text-[#99B29B]' : 'text-red-500'}`}>
                            {isPositive ? '+' : ''}{val.toFixed(4)}
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-[#FAF7F2] h-2 rounded-full relative overflow-hidden">
                        <div 
                           className={`h-full rounded-full absolute ${isPositive ? 'bg-[#99B29B] left-1/2' : 'bg-red-400 right-1/2'}`}
                          style={{ 
                            width: `${absPercent / 2}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-[#6B6864] italic text-xs">
                No SHAP attributions found for this account. Make sure model is trained.
              </div>
            )}
          </AlephCard>

          {/* Copilot Report (Right 3 columns) */}
          <AlephCard className="xl:col-span-3 p-8 flex flex-col h-[560px] justify-between">
            <div>
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">AI Analyst Copilot</span>
                  <h3 className="text-xl font-serif font-bold text-[#2D2D2D] mt-0.5">Compliance SAR Case Dossier</h3>
                  <p className="text-xs text-[#6B6864] font-light mt-0.5">Auto-generated filing draft based on structural graph signals.</p>
                </div>
                
                <div className="flex space-x-3">
                  <button 
                    onClick={copyToClipboard}
                    className="px-3.5 py-2 border border-[#EAE1D4] text-[#2D2D2D] hover:bg-[#FAF7F2] rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all"
                  >
                    {copiedCopilot ? 'Copied!' : 'Copy Report'}
                  </button>
                  <button 
                    onClick={handleDownloadReport}
                    className="px-3.5 py-2 bg-[#2D2D2D] text-white hover:bg-black rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all shadow-sm"
                  >
                    📥 Export SAR
                  </button>
                </div>
              </div>

              {loadingDetails ? (
                <div className="flex flex-col items-center justify-center py-24">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-[#99B29B] mb-2"></div>
                  <p className="text-[10px] text-[#6B6864] uppercase tracking-wider">Generating SAR narrative...</p>
                </div>
              ) : (
                <textarea 
                  value={copilotReport} 
                  readOnly
                  className="w-full h-[400px] border border-[#EAE1D4] rounded-lg p-6 bg-[#FAF7F2]/50 font-mono text-[11px] leading-relaxed text-[#2D2D2D] focus:outline-none overflow-y-auto resize-none"
                />
              )}
            </div>
          </AlephCard>

        </div>
      )}

      {/* STR Verification Layer */}
      {activeSection === 'str-alignment' && (
        <div className="space-y-10">
          
          <AlephCard className="p-8">
            <div className="mb-6">
              <h3 className="text-xl font-serif font-bold text-[#2D2D2D]">STR Claims Narrative Verification Dashboard</h3>
              <p className="text-xs text-[#6B6864] font-light mt-0.5">Validating legal report testimonies against computed multi-hop transfer pathways.</p>
            </div>
            
            {loadingDetails ? (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-[#99B29B] mb-2"></div>
                <p className="text-[10px] text-[#6B6864] uppercase tracking-wider">Comparing evidence...</p>
              </div>
            ) : claims.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div>
                  <h4 className="text-sm font-serif font-semibold text-[#2D2D2D] mb-4">Pending Alignments for Account {selectedAccountId}</h4>
                  <div className="space-y-4">
                    {claims.map((claim, idx) => (
                      <div key={idx} className="p-4 border border-[#EAE1D4] rounded-lg">
                        <div className="flex justify-between items-start">
                           <h5 className="text-xs font-bold font-mono text-[#2D2D2D]">{claim.text}</h5>
                          <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase ${
                            claim.status === 'CONFIRMED' || claim.status === 'VERIFIED' ? 'bg-[#99B29B]/15 text-[#99B29B]' : 'bg-red-100 text-red-700'
                          }`}>
                            {claim.status}
                          </span>
                        </div>
                        <p className="text-xs text-[#6B6864] font-light mt-2">{claim.details}</p>
                        <div className="text-[9px] text-[#6B6864] mt-3 font-mono flex justify-between">
                          <span>Report Reference: {claim.reportId}</span>
                          <span>Alignment Engine v3</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-[#FAF7F2]/50 border border-[#EAE1D4] rounded-lg p-6 flex flex-col justify-between">
                  <div>
                    <h4 className="text-sm font-serif font-semibold text-[#2D2D2D] mb-3">Verification Rationale</h4>
                    <p className="text-xs text-[#6B6864] leading-relaxed font-light mb-4">
                      The Narrative Claims alignment engine extracts testimonies (dates, amounts, bank names, and transfer mechanisms) 
                      from compliance officer texts using phonetic & levenshtein string resolution rules.
                    </p>
                    <p className="text-xs text-[#6B6864] leading-relaxed font-light">
                      It cross-checks these references directly against the continuous-time multigraph edge listings. 
                      If matching nodes exhibit the stated behaviors, they are tagged as <strong className="text-[#99B29B]">CONFIRMED</strong>. 
                      If no matching edge traces are found or threshold criteria are not reached, they are logged as <strong className="text-red-500">REFUTED</strong>.
                    </p>
                  </div>
                  <div className="pt-6 border-t border-[#EAE1D4] flex justify-between items-center">
                    <span className="text-[10px] font-bold text-[#6B6864] uppercase tracking-wider">Claims Matched: {claims.length}</span>
                    <button 
                      onClick={() => setActiveSection('topology')}
                      className="text-[#99B29B] font-bold tracking-wider uppercase text-[10px]"
                    >
                      Return to Flow Map →
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-[#6B6864] italic py-10 text-center">No active narrative claims found linking this entity.</p>
            )}
          </AlephCard>
          
        </div>
      )}

    </WorkspaceShell>
  );
}
