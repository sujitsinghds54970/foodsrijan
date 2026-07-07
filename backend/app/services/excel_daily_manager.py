"""
Excel Daily Entry Manager - Production Ready
Branch-separated Excel files with pandas/openpyxl
Concurrent access safe with lock + retry
"""

import os
import logging
import threading
import time
import shutil
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import json
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BranchConfig:
    """Branch configuration"""
    branch_id: str
    branch_name: str
    base_data_path: str = "./data"

LOCK_TIMEOUT = 30  # seconds
RETRY_DELAY
