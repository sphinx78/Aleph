"""
ALEPH Analyst Copilot Module

Integrates local LLM APIs (Ollama) with fallback template engines to:
- Auto-generate legal-grade Suspicious Activity Reports (SAR)
- Compile comprehensive case files for FIU (Financial Intelligence Unit) compliance.
"""

import requests
import json
import pandas as pd
from typing import Dict, Any, List
from src.utils import setup_logger

logger = setup_logger()

class AnalystCopilot:
    """
    Orchestrates compliance case documentation, using local language models (Ollama)
    or a high-fidelity deterministic fallback template.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate", model_name: str = "llama3"):
        self.ollama_url = ollama_url
        self.model_name = model_name
        
    def check_ollama_status(self) -> bool:
        """Verifies if the local Ollama LLM endpoint is active."""
        try:
            # Short timeout to avoid blocking if Ollama is not installed/running
            response = requests.get(self.ollama_url.replace("/api/generate", ""), timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False

    def generate_case_summary(self, case_details: Dict[str, Any]) -> str:
        """
        Generates a professional compliance review summary for an account.
        """
        # Formulate system prompt & context
        prompt = (
            "You are an expert Anti-Money Laundering (AML) Compliance Analyst. "
            "Generate a professional, structured case summary for the Financial Intelligence Unit (FIU) "
            "based on the following structured evidence:\n\n"
            f"Account ID: {case_details.get('account_id')}\n"
            f"Fused Risk Score: {case_details.get('risk_score', 0.0):.3f} ({case_details.get('risk_band')}, Rank #{case_details.get('rank')})\n"
            f"Risk Drivers: {json.dumps(case_details.get('risk_drivers', {}))}\n"
            f"Detected Typologies: {', '.join(case_details.get('typologies', []))}\n"
            f"Narrative Claims Verification: {json.dumps(case_details.get('verification_claims', {}))}\n"
            f"Transaction Summary: Inbound Vol = {case_details.get('in_volume', 0.0):,.2f} NPR, Outbound Vol = {case_details.get('out_volume', 0.0):,.2f} NPR\n\n"
            "Provide the report in four parts: 1. EXECUTIVE SUMMARY, 2. BEHAVIORAL ANALYSIS, 3. EVIDENCE VERIFICATION, and 4. RECOMMENDED COMPLIANCE ACTION."
        )
        
        if self.check_ollama_status():
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
                logger.info("Generating summary via Ollama LLM...")
                response = requests.post(self.ollama_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return response.json().get('response', '')
            except Exception as e:
                logger.warning(f"Ollama call failed, falling back to template engine: {e}")
                
        # Deterministic High-Fidelity Fallback
        return self._generate_template_summary(case_details)

    def _generate_template_summary(self, case_details: Dict[str, Any]) -> str:
        """Generates a structured legal-grade compliance report using deterministic analysis."""
        acc_id = case_details.get('account_id')
        risk_score = case_details.get('risk_score', 0.0)
        risk_band = case_details.get('risk_band', 'UNKNOWN')
        rank = case_details.get('rank', 'N/A')
        in_vol = case_details.get('in_volume', 0.0)
        out_vol = case_details.get('out_volume', 0.0)
        
        typologies = case_details.get('typologies', [])
        claims = case_details.get('verification_claims', {})
        drivers = case_details.get('risk_drivers', {})
        
        # Format lists
        typology_str = ", ".join(typologies) if typologies else "No rule-based typologies flagged."
        
        claims_str = ""
        for claim, status in claims.items():
            claims_str += f"   - Claim '{claim}' status: {status}\n"
        if not claims_str:
            claims_str = "   - No claims matched to XML report registries."
            
        driver_str = ""
        for k, v in drivers.items():
            driver_str += f"   - {k.replace('_', ' ').capitalize()}: {v:.2%}\n"
            
        report = f"""================================================================================
SUSPICIOUS ACTIVITY REPORT (SAR) / COMPLIANCE CASE DOSSIER
================================================================================
CASE PROFILE: Account {acc_id}
RISK RATING: {risk_band} (Score: {risk_score:.3f} | Rank: #{rank})
--------------------------------------------------------------------------------

1. EXECUTIVE SUMMARY:
   Account {acc_id} has been flagged for critical suspicion by the ALEPH multi-layer
   knowledge mesh. The account exhibits anomalous flow behaviors with a total inbound
   volume of {in_vol:,.2f} NPR and outbound volume of {out_vol:,.2f} NPR, presenting a
   flow ratio of {out_vol/(in_vol+1e-5):.2f}. Fused risk metrics place this entity in the
   {risk_band} bracket, warranting immediate investigation and submission of formal filings.

2. BEHAVIORAL ANALYSIS:
   The primary risk drivers contributing to this classification include:
{driver_str}
   FLAGGED TYPOLOGIES:
   - {typology_str}

3. EVIDENCE VERIFICATION:
   Narrative claims extracted from matching Suspicious Transaction Reports (STRs)
   were cross-validated against transaction graph evidence:
{claims_str}

4. RECOMMENDED COMPLIANCE ACTION:
   Based on the high risk score ({risk_score:.3f}) and confirmed typology behaviors, the
   compliance desk recommends:
   [X] Freeze account pending immediate administrative audit of all counterparties.
   [X] Draft and submit Suspicious Activity Report (SAR) to the Financial Intelligence Unit (FIU).
   [X] Coordinate with clearing counterparties to perform reverse tracing of layering sources.
================================================================================
"""
        return report
