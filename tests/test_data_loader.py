"""
Unit tests for src/data_loader.py
"""

import unittest
import pandas as pd
from src.data_loader import calculate_soundex, AMLDataParser, NarrativeEvidenceVerifier

class TestDataLoader(unittest.TestCase):
    def test_calculate_soundex(self):
        # Basic match
        self.assertEqual(calculate_soundex("Robert"), calculate_soundex("Rupert"))
        # Specific examples
        self.assertEqual(calculate_soundex("Ashcraft"), "A261")
        self.assertEqual(calculate_soundex("Ashcroft"), "A261")
        
    def test_entity_resolution_logic(self):
        # Mock dataframe setup
        accounts_data = {
            'account_id': [1, 2],
            'tax_number': ['123', '456'],
            'name': ['John Smith', 'Robert Jones']
        }
        parser = AMLDataParser(raw_dir='dummy', reports_dir='dummy', processed_dir='dummy')
        parser.accounts_df = pd.DataFrame(accounts_data)
        
        extracted_data = {
            'report_id': ['R1', 'R2', 'R3'],
            'first_name': ['John', 'Rupert', 'Unknown'],
            'last_name': ['Smith', 'Jones', 'Guy'],
            'tax_number': ['123', '999', '000'], # 123 is direct match
            'narrative': ['Test', 'Test', 'Test']
        }
        extracted_df = pd.DataFrame(extracted_data)
        
        # Test the matching
        linked_df = parser.match_and_link_entities(extracted_df)
        
        self.assertFalse(linked_df.empty)
        # Should match John Smith via tax_number
        direct_matches = linked_df[linked_df['match_method'] == 'direct_identifier']
        self.assertEqual(len(direct_matches), 1)
        self.assertEqual(direct_matches.iloc[0]['registry_id'], 1)

class TestNarrativeEvidenceVerifier(unittest.TestCase):
    def test_extract_claims(self):
        verifier = NarrativeEvidenceVerifier(processed_dir='dummy')
        claims = verifier.extract_claims("This was a huge international wire transfer.")
        self.assertIn('cross_border_activity', claims)
        self.assertIn('high_volume', claims)

if __name__ == '__main__':
    unittest.main()
