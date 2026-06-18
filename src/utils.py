"""
ALEPH Utilities Module

Handles:
- Logging configuration
- Path constants for data directories
- Common mathematical helper functions
"""

import logging
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "STUDENT_DATASET"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = RAW_DATA_DIR / "reports"

# Ensure directories exist
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

def setup_logger(name="ALEPH"):
    """Configures and returns a logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Create console handler and set level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # Add formatter to ch
        ch.setFormatter(formatter)
        # Add ch to logger
        logger.addHandler(ch)
    return logger
