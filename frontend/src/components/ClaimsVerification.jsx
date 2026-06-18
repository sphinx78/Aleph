import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

export default function ClaimsVerification({ claimsList }) {
  if (!claimsList || claimsList.length === 0) {
    return (
      <div className="bg-white border border-[#EAE1D4] rounded-xl p-6">
        <div className="mb-6">
          <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
            Verification Systems
          </span>
          <h4 className="text-sm font-serif font-semibold text-[#2D2D2D]">
            Narrative Claims vs. Transaction Graph Evidence
          </h4>
        </div>
        <p className="text-xs text-[#6B6864] italic">No active narrative claims found linking this entity.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-[#EAE1D4] rounded-xl p-6">
      <div className="mb-6">
        <span className="text-[9px] uppercase tracking-[0.2em] text-[#C07A50] font-bold">
          Verification Systems
        </span>
        <h4 className="text-sm font-serif font-semibold text-[#2D2D2D]">
          Narrative Claims vs. Transaction Graph Evidence
        </h4>
      </div>

      <div className="space-y-3">
        {claimsList.map((claim, idx) => {
          const isConfirmed = claim.status === 'CONFIRMED' || claim.status === 'VERIFIED';
          return (
            <div 
              key={idx} 
              className={`flex items-center justify-between p-4 rounded-lg border transition-all ${
                isConfirmed 
                  ? 'bg-[#99B29B]/5 border-[#99B29B]/30' 
                  : 'bg-red-50/40 border-red-200'
              }`}
            >
              <div className="flex items-center space-x-3">
                {isConfirmed ? (
                  <CheckCircle2 className="w-5 h-5 text-[#99B29B] shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-500 shrink-0" />
                )}
                <div>
                  <p className="text-xs font-semibold text-[#2D2D2D]">{claim.text}</p>
                  <p className="text-[10px] text-[#6B6864] mt-0.5">{claim.details}</p>
                </div>
              </div>
              
              <div className="text-right">
                <span className={`inline-block text-[9px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${
                  isConfirmed 
                    ? 'bg-[#99B29B]/15 text-[#99B29B]' 
                    : 'bg-red-100 text-red-700'
                }`}>
                  {claim.status}
                </span>
                <p className="text-[9px] font-mono text-[#6B6864] mt-1">Ref: {claim.reportId}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
