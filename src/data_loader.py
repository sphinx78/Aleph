"""
ALEPH Data Loader Module

Handles:
- Loading CSV datasets (transactions, accounts, graph edges, ML features)
- Parsing STR XML reports from the reports/ directory
- Enhanced phonetic entity resolution using Soundex and Levenshtein fuzzy string similarity
- STR narrative evidence verification against transaction graph features
"""

import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
import re
import Levenshtein
import logging
from typing import Dict, List, Optional
from src.utils import setup_logger, RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR

logger = setup_logger()

def calculate_soundex(name: str) -> str:
    """
    Computes the standard US Census Soundex code for string matching.
    """
    if not name or not isinstance(name, str):
        return ""
    name = name.upper()
    cleaned = re.sub(r'[^A-Z]', '', name)
    if not cleaned:
        return ""
    
    first_char = cleaned[0]
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    
    first_digit = mapping.get(first_char, '0')
    soundex_digits = []
    prev_digit = first_digit
    
    for char in cleaned[1:]:
        digit = mapping.get(char, '0')
        if digit != '0':
            if digit != prev_digit:
                soundex_digits.append(digit)
            prev_digit = digit
        else:
            if char in 'AEIOUY':
                prev_digit = '0'
            
    soundex_str = first_char + "".join(soundex_digits)
    soundex_str = (soundex_str + "000")[:4]
    return soundex_str

class AMLDataParser:
    """
    Parses STR XML reports and links referenced entities to the KYC registry 
    using phonetic and alphanumeric matching.
    """
    def __init__(self, raw_dir=RAW_DATA_DIR, reports_dir=REPORTS_DIR, processed_dir=PROCESSED_DATA_DIR):
        self.raw_dir = raw_dir
        self.reports_dir = reports_dir
        self.processed_dir = processed_dir
        self.transactions_df: Optional[pd.DataFrame] = None
        self.accounts_df: Optional[pd.DataFrame] = None
        self.graph_edges_df: Optional[pd.DataFrame] = None
        
    def load_transactions(self) -> pd.DataFrame:
        """Loads the main transactions dataset."""
        path = self.raw_dir / "transactions.csv"
        logger.info(f"Loading transactions from {path}...")
        self.transactions_df = pd.read_csv(path)
        return self.transactions_df
        
    def _compute_phonetic_cols(self):
        """Pre-calculates phonetic codes for the current accounts dataframe."""
        if self.accounts_df is None:
            return
        
        # Ensure tax_number is string for exact matching later
        if 'tax_number' in self.accounts_df.columns:
            self.accounts_df['tax_number'] = self.accounts_df['tax_number'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
            
        logger.info("Calculating Soundex for accounts...")
        self.accounts_df['name'] = self.accounts_df['name'].fillna('')
        
        def split_name_soundex(full_name: str, part: str = 'first') -> str:
            parts = str(full_name).strip().split()
            if not parts:
                return ""
            if part == 'first':
                return calculate_soundex(parts[0])
            else:
                return calculate_soundex(parts[-1]) if len(parts) > 1 else ""
                
        self.accounts_df['phonetic_first'] = self.accounts_df['name'].apply(lambda x: split_name_soundex(x, 'first'))
        self.accounts_df['phonetic_last'] = self.accounts_df['name'].apply(lambda x: split_name_soundex(x, 'last'))

    def load_accounts(self) -> pd.DataFrame:
        """Loads the accounts KYC dataset and pre-computes phonetic codes."""
        path = self.raw_dir / "accounts.csv"
        logger.info(f"Loading accounts from {path}...")
        self.accounts_df = pd.read_csv(path)
        self._compute_phonetic_cols()
        return self.accounts_df
        
    def load_graph_edges(self) -> pd.DataFrame:
        """Loads the pre-computed graph edges."""
        path = self.raw_dir / "graph_edges.csv"
        logger.info(f"Loading graph edges from {path}...")
        self.graph_edges_df = pd.read_csv(path)
        return self.graph_edges_df
        
    def parse_all_xml_reports(self) -> pd.DataFrame:
        """Parses all STR XML files in reports directory to extract narratives and entities."""
        logger.info(f"Parsing XML reports in {self.reports_dir}...")
        extracted_data = []
        xml_files = glob.glob(str(self.reports_dir / "*.xml"))
        
        if not xml_files:
            logger.warning(f"No XML files found in {self.reports_dir}")
            return pd.DataFrame()
            
        for xml_path in xml_files:
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Each file usually has one <report> root, but handle multiple just in case
                for report in root.findall('.//report') or [root]:
                    report_id = report.findtext('report_id') or os.path.basename(xml_path)
                    
                    narrative_text = report.findtext('reason', '')
                    if not narrative_text:
                        # Fallback heuristic: find longest text block if <reason> missing
                        for elem in report.iter():
                            if elem.text and len(elem.text.strip()) > 150:
                                narrative_text = elem.text.strip()
                                break
                                
                    # Extract all transactional parties mentioned in the report
                    for person in report.findall('.//t_person'):
                        extracted_data.append({
                            'report_id': report_id,
                            'first_name': person.findtext('first_name', ''),
                            'last_name': person.findtext('last_name', ''),
                            'passport_number': person.findtext('passport_number', ''),
                            'tax_number': person.findtext('tax_number', ''),
                            'narrative': narrative_text
                        })
            except ET.ParseError as e:
                logger.error(f"XML parse error in {xml_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error parsing {xml_path}: {e}")
                
        df = pd.DataFrame(extracted_data)
        logger.info(f"Extracted {len(df)} entity records from {len(xml_files)} reports.")
        return df

    def match_and_link_entities(self, extracted_entities_df: pd.DataFrame) -> pd.DataFrame:
        """
        Matches extracted STR entities to the KYC accounts registry 
        using deterministic (tax/ID), phonetic (Soundex) and fuzzy string (Levenshtein) logic.
        """
        logger.info("Matching and linking entities using enhanced phonetics + Levenshtein...")
        if extracted_entities_df.empty:
            logger.warning("No extracted entities provided to match.")
            return pd.DataFrame()
            
        if self.accounts_df is None:
            self.load_accounts()
        elif 'phonetic_first' not in self.accounts_df.columns or 'phonetic_last' not in self.accounts_df.columns:
            logger.info("Phonetic columns missing from accounts dataframe. Computing them now...")
            self._compute_phonetic_cols()
            
        links = []
        for idx, row in extracted_entities_df.iterrows():
            str_first = str(row.get('first_name', '')).strip()
            str_last = str(row.get('last_name', '')).strip()
            str_tax = str(row.get('tax_number', '')).strip()
            str_full_name = f"{str_first} {str_last}".strip()
            
            # 1. Direct Identifier Match (Priority)
            if str_tax:
                str_tax_clean = str_tax.split('.')[0]
                direct_match = self.accounts_df[self.accounts_df['tax_number'] == str_tax_clean]
                if not direct_match.empty:
                    links.append({
                        'report_id': row['report_id'],
                        'str_entity': str_full_name,
                        'registry_id': direct_match.iloc[0]['account_id'],
                        'match_method': 'direct_identifier',
                        'confidence': 1.0,
                        'narrative': row['narrative']
                    })
                    continue
                
            # 2. Enhanced Phonetic + Fuzzy Match Pipeline
            phon_first = calculate_soundex(str_first)
            phon_last = calculate_soundex(str_last)
            
            if phon_first and phon_last:
                phonetic_matches = self.accounts_df[
                    (self.accounts_df['phonetic_first'] == phon_first) & 
                    (self.accounts_df['phonetic_last'] == phon_last)
                ]
                
                for _, match_row in phonetic_matches.iterrows():
                    kyc_name = str(match_row['name']).strip()
                    # Calculate Levenshtein similarity ratio between full names
                    sim_ratio = Levenshtein.ratio(str_full_name.lower(), kyc_name.lower())
                    
                    # Confidence is scaling of phonetic match adjusted by name similarity
                    confidence = 0.60 + 0.38 * sim_ratio
                    
                    links.append({
                        'report_id': row['report_id'],
                        'str_entity': str_full_name,
                        'registry_id': match_row['account_id'],
                        'match_method': 'phonetic_fuzzy_match',
                        'confidence': round(confidence, 3),
                        'narrative': row['narrative']
                    })
                    
        linked_df = pd.DataFrame(links)
        logger.info(f"Successfully matched {len(linked_df)} entities to registry.")
        return linked_df

    def save_processed(self, df: pd.DataFrame, filename: str = "extracted_entities.csv"):
        """Saves a dataframe to the processed data directory."""
        path = self.processed_dir / filename
        df.to_csv(path, index=False)
        logger.info(f"Saved processed data to {path}")

class NarrativeEvidenceVerifier:
    """
    Cross-validates unstructured narrative claims in STR reports 
    against structural evidence in the transaction graph.
    """
    def __init__(self, processed_dir=PROCESSED_DATA_DIR):
        self.processed_dir = processed_dir
        
    def extract_claims(self, narrative_text: str) -> List[str]:
        """Extracts claim types from text using keyword heuristics."""
        claims = []
        text = str(narrative_text).lower()
        if re.search(r'cross-border|international|foreign|abroad|overseas', text):
            claims.append('cross_border_activity')
        if re.search(r'large|high value|huge|millions|lakhs|heavy amount', text):
            claims.append('high_volume')
        if re.search(r'rapid|quick|immediate|velocity|fast|burst', text):
            claims.append('rapid_movement')
        return claims
        
    def verify_claim(self, claim_type: str, account_id, graph_engine) -> str:
        """Checks graph metrics to confirm or refute a claim."""
        account_id_str = str(account_id)
        if account_id_str not in graph_engine.node_features:
            return "NOT_FOUND"
            
        features = graph_engine.node_features[account_id_str]
        
        if claim_type == 'cross_border_activity':
            # Check community risk indices or GNN embeddings
            return "CONFIRMED" if (features.get('comm_cb_ratio', 0) > 0.05 or features.get('emb_tgat_0', 0) != 0) else "REFUTED"
        elif claim_type == 'high_volume':
            # Confirmation boundary: in+out volume > 1,000,000 NPR
            in_vol = features.get('in_volume', 0.0)
            out_vol = features.get('out_volume', 0.0)
            return "CONFIRMED" if (in_vol + out_vol) > 1000000.0 else "REFUTED"
        elif claim_type == 'rapid_movement':
            # Confirmation boundary: Hawkes process intensity > 0.3
            return "CONFIRMED" if (features.get('hawkes_intensity', 0.0) > 0.3 or features.get('motif_cycle', 0) > 0) else "REFUTED"
            
        return "UNKNOWN"
        
    def verify_all_reports(self, linked_entities_df: pd.DataFrame, graph_engine) -> pd.DataFrame:
        """Processes all linked entities and validates their narratives."""
        logger.info("Validating narrative claims against graph evidence...")
        results = []
        for _, row in linked_entities_df.iterrows():
            acc_id = row['registry_id']
            claims = self.extract_claims(row['narrative'])
            
            for claim in claims:
                status = self.verify_claim(claim, acc_id, graph_engine)
                results.append({
                    'report_id': row['report_id'],
                    'account_id': acc_id,
                    'claim_type': claim,
                    'verification_status': status
                })
                
        results_df = pd.DataFrame(results)
        logger.info(f"Verified {len(results_df)} claims across {len(linked_entities_df)} linked entities.")
        return results_df
        
    def export_verification(self, df: pd.DataFrame, filename: str = "str_verification.csv"):
        """Saves verification matrix."""
        path = self.processed_dir / filename
        if not df.empty:
            df.to_csv(path, index=False)
            logger.info(f"Exported STR verification to {path}")
