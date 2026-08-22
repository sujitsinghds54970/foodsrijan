"""
Multi-Branch Diagnostic ERP System - Daily Entry Excel Manager
================================================================

This module provides comprehensive Excel-based patient record management for a multi-branch
diagnostic company. Each branch maintains separate Excel files organized by daily, monthly,
and yearly views with complete data isolation between branches.

Author: Vaidya Vihar Diagnostic ERP Team
Version: 2.0.0
Last Updated: 2026-03-22

Features:
- Branch-specific Excel file management
- Daily, Monthly, and Yearly reporting
- Customer record CRUD operations
- Data archiving and backup
- Branch transfer functionality
- Concurrent access handling
- Comprehensive logging and error handling
"""

import os
import json
import logging
import shutil
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from functools import wraps
import traceback

# Excel and Data Processing
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
import pandas as pd

# PDF Export
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

@dataclass
class BranchConfig:
    """Branch-specific configuration"""
    BRANCH_ID: str = "BRANCH_001"
    BRANCH_NAME: str = "City Center Lab"
    BRANCH_CODE: str = "CCL"  # Short code for patient IDs
    BASE_DATA_PATH: str = "C:/ERP_Data/{BRANCH_ID}/"
    
    # File naming patterns
    DAILY_LOG_PATTERN: str = "Daily_Customer_Log_{BRANCH_ID}_{YEAR}_{MONTH}.xlsx"
    YEARLY_SUMMARY_PATTERN: str = "{YEAR}_Summary.xlsx"
    
    # Folder structure
    ARCHIVE_FOLDER: str = "Archive"
    SUMMARIES_FOLDER: str = "Summaries"
    BACKUP_FOLDER: str = "Backups"
    EXPORTS_FOLDER: str = "Exports"
    CONFIG_FOLDER: str = "Config"
    
    # Performance settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: float = 0.5
    FILE_LOCK_TIMEOUT: int = 30
    
    # Data validation
    MAX_PATIENT_NAME_LENGTH: int = 100
    MAX_NOTES_LENGTH: int = 500
    VALID_GENDERS: List[str] = None
    VALID_STATUSES: List[str] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.VALID_GENDERS is None:
            self.VALID_GENDERS = ["Male", "Female", "Other"]
        if self.VALID_STATUSES is None:
            self.VALID_STATUSES = ["Pending", "In Progress", "Completed", "Cancelled"]
        
        # Expand path with branch ID
        self.BASE_DATA_PATH = self.BASE_DATA_PATH.format(BRANCH_ID=self.BRANCH_ID)
    
    def get_full_path(self, *parts: str) -> str:
        """Get full path by joining base path with parts"""
        return os.path.join(self.BASE_DATA_PATH, *parts)
    
    def save_to_file(self, filepath: Optional[str] = None) -> None:
        """Save configuration to JSON file"""
        if filepath is None:
            filepath = self.get_full_path(self.CONFIG_FOLDER, "branch_config.json")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=4)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'BranchConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


# ============================================================================
# EXCEL COLUMN DEFINITIONS
# ============================================================================

class ExcelColumns:
    """Excel column definitions and headers"""
    TIMESTAMP = "A"
    PATIENT_ID = "B"
    PATIENT_NAME = "C"
    AGE = "D"
    GENDER = "E"
    TEST_TYPE = "F"
    REFERRING_DOCTOR = "G"
    STATUS = "H"
    CONTACT_NUMBER = "I"
    NOTES = "J"
    BRANCH_ID = "K"
    CREATED_BY = "L"
    LAST_UPDATED = "M"
    IS_ARCHIVED = "N"
    
    HEADERS = [
        "Timestamp",
        "Customer ID",
        "Customer Name",
        "Age",
        "Gender",
        "MenuItem Type",
        "Referring Staff",
        "Status",
        "Contact Number",
        "Notes",
        "Branch ID",
        "Created By",
        "Last Updated",
        "Is Archived"
    ]
    
    @classmethod
    def get_column_index(cls, column_name: str) -> int:
        """Get 1-based column index from column letter"""
        return openpyxl.utils.column_index_from_string(getattr(cls, column_name))
    
    @classmethod
    def get_all_columns(cls) -> List[str]:
        """Get all column letters"""
        return [getattr(cls, attr) for attr in dir(cls) 
                if not attr.startswith('_') and attr.isupper() and len(getattr(cls, attr)) <= 2]


# ============================================================================
# PATIENT DATA MODEL
# ============================================================================

@dataclass
class CustomerRecord:
    """Customer record data model"""
    patient_id: str
    patient_name: str
    age: int
    gender: str
    test_type: str
    referring_doctor: str
    status: str
    contact_number: str
    notes: str
    branch_id: str
    created_by: str
    timestamp: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    is_archived: bool = False
    
    def __post_init__(self):
        """Initialize timestamps if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime to string for JSON serialization
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        if isinstance(data['last_updated'], datetime):
            data['last_updated'] = data['last_updated'].isoformat()
        return data
    
    def to_excel_row(self) -> List[Any]:
        """Convert to Excel row format"""
        return [
            self.timestamp,
            self.patient_id,
            self.patient_name,
            self.age,
            self.gender,
            self.test_type,
            self.referring_doctor,
            self.status,
            self.contact_number,
            self.notes,
            self.branch_id,
            self.created_by,
            self.last_updated,
            self.is_archived
        ]
    
    @classmethod
    def from_excel_row(cls, row: List[Any], branch_id: str) -> 'CustomerRecord':
        """Create CustomerRecord from Excel row"""
        return cls(
            timestamp=row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0])),
            patient_id=str(row[1]),
            patient_name=str(row[2]),
            age=int(row[3]),
            gender=str(row[4]),
            test_type=str(row[5]),
            referring_doctor=str(row[6]),
            status=str(row[7]),
            contact_number=str(row[8]),
            notes=str(row[9]),
            branch_id=str(row[10]) if len(row) > 10 else branch_id,
            created_by=str(row[11]) if len(row) > 11 else "System",
            last_updated=row[12] if len(row) > 12 and isinstance(row[12], datetime) else datetime.now(),
            is_archived=bool(row[13]) if len(row) > 13 else False
        )


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class DailyEntryError(Exception):
    """Base exception for daily entry operations"""
    def __init__(self, message: str, error_code: str = "DE_ERROR", branch_id: str = ""):
        self.message = message
        self.error_code = error_code
        self.branch_id = branch_id
        super().__init__(f"[{error_code}] {message} (Branch: {branch_id})")


class BranchConfigError(DailyEntryError):
    """Branch configuration error"""
    def __init__(self, message: str, branch_id: str = ""):
        super().__init__(message, "DE_CONFIG_ERROR", branch_id)


class FileAccessError(DailyEntryError):
    """File access error"""
    def __init__(self, message: str, branch_id: str = ""):
        super().__init__(message, "DE_FILE_ERROR", branch_id)


class DataValidationError(DailyEntryError):
    """Data validation error"""
    def __init__(self, message: str, branch_id: str = ""):
        super().__init__(message, "DE_VALIDATION_ERROR", branch_id)


class CustomerNotFoundError(DailyEntryError):
    """Customer not found error"""
    def __init__(self, message: str, branch_id: str = ""):
        super().__init__(message, "DE_NOT_FOUND", branch_id)


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logger(branch_id: str, log_path: Optional[str] = None) -> logging.Logger:
    """Setup branch-specific logger"""
    logger = logging.getLogger(f"DailyEntry_{branch_id}")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        f'%(asctime)s - [{branch_id}] - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            f'%(asctime)s - [{branch_id}] - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# UTILITY DECORATORS AND FUNCTIONS
# ============================================================================

def retry_on_failure(max_attempts: int = 3, delay: float = 0.5):
    """Decorator to retry function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    continue
            raise last_exception
        return wrapper
    return decorator


def log_operation(operation_name: str):
    """Decorator to log operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.logger.info(f"Starting operation: {operation_name}")
            try:
                result = func(self, *args, **kwargs)
                self.logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                self.logger.error(f"Failed operation: {operation_name} - {str(e)}")
                raise
        return wrapper
    return decorator


# ============================================================================
# FILE LOCKING MECHANISM
# ============================================================================

class FileLock:
    """Thread-safe file locking mechanism"""
    
    def __init__(self, timeout: int = 30):
        self._lock = threading.Lock()
        self._timeout = timeout
        self._locked_files: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()
    
    @contextmanager
    def acquire(self, filepath: str):
        """Acquire lock for a specific file"""
        # Get or create lock for this file
        with self._locks_lock:
            if filepath not in self._locked_files:
                self._locked_files[filepath] = threading.Lock()
            file_lock = self._locked_files[filepath]
        
        # Try to acquire the lock
        acquired = file_lock.acquire(timeout=self._timeout)
        if not acquired:
            raise FileAccessError(f"Could not acquire lock for file: {filepath}")
        
        try:
            yield
        finally:
            file_lock.release()


# ============================================================================
# STATISTICS CACHE
# ============================================================================

class StatisticsCache:
    """Cache for branch statistics"""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value"""
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def invalidate(self, key: str = None) -> None:
        """Invalidate cache entry or all entries"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()


# ============================================================================
# MAIN DAILY ENTRY MANAGER CLASS
# ============================================================================

class DailyEntryManager:
    """
    Main class for managing daily patient entries with Excel-based storage.
    Provides comprehensive functionality for multi-branch diagnostic ERP system.
    """
    
    def __init__(self, config: BranchConfig):
        """
        Initialize DailyEntryManager
        
        Args:
            config: Branch configuration object
        """
        self.config = config
        self.branch_id = config.BRANCH_ID
        self.branch_name = config.BRANCH_NAME
        
        # Setup logging
        log_path = config.get_full_path("Logs", f"{config.BRANCH_ID}_daily_entry.log")
        self.logger = setup_logger(config.BRANCH_ID, log_path)
        
        # File locking
        self.file_lock = FileLock(timeout=config.FILE_LOCK_TIMEOUT)
        
        # Statistics cache
        self.stats_cache = StatisticsCache(ttl_seconds=config.CACHE_TTL_SECONDS) if config.CACHE_ENABLED else None
        
        # Customer ID counter lock
        self._id_counter_lock = threading.Lock()
        
        self.logger.info(f"Initialized DailyEntryManager for branch: {self.branch_name} ({self.branch_id})")
    
    # ========================================================================
    # INITIALIZATION AND SETUP
    # ========================================================================
    
    @log_operation("Initialize Branch Structure")
    def initialize_branch_structure(self) -> Dict[str, str]:
        """
        Create complete folder structure for the branch
        
        Returns:
            Dictionary with created folder paths
        """
        folders = {
            'base': self.config.BASE_DATA_PATH,
            'archive': self.config.get_full_path(self.config.ARCHIVE_FOLDER),
            'summaries': self.config.get_full_path(self.config.SUMMARIES_FOLDER),
            'backups': self.config.get_full_path(self.config.BACKUP_FOLDER),
            'exports': self.config.get_full_path(self.config.EXPORTS_FOLDER),
            'config': self.config.get_full_path(self.config.CONFIG_FOLDER),
            'logs': self.config.get_full_path("Logs"),
        }
        
        for folder_name, folder_path in folders.items():
            try:
                os.makedirs(folder_path, exist_ok=True)
                self.logger.debug(f"Created/verified folder: {folder_name} at {folder_path}")
            except Exception as e:
                raise BranchConfigError(
                    f"Failed to create folder {folder_name}: {str(e)}",
                    self.branch_id
                )
        
        # Save configuration
        self.config.save_to_file()
        self.logger.info("Branch structure initialized successfully")
        
        return folders
    
    def get_current_excel_file(self, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """
        Get path to current month's Excel file
        
        Args:
            year: Year (default: current year)
            month: Month (default: current month)
        
        Returns:
            Full path to Excel file
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        
        filename = self.config.DAILY_LOG_PATTERN.format(
            BRANCH_ID=self.config.BRANCH_ID,
            YEAR=year,
            MONTH=f"{month:02d}"
        )
        
        filepath = self.config.get_full_path(filename)
        
        # Create file if it doesn't exist
        if not os.path.exists(filepath):
            self._create_new_excel_file(filepath)
        
        return filepath
    
    def _create_new_excel_file(self, filepath: str) -> None:
        """Create a new Excel file with headers"""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Customer Records"
            
            # Add headers
            ws.append(ExcelColumns.HEADERS)
            
            # Format headers
            self._format_header_row(ws)
            
            # Save workbook
            wb.save(filepath)
            self.logger.info(f"Created new Excel file: {filepath}")
            
        except Exception as e:
            raise FileAccessError(f"Failed to create Excel file: {str(e)}", self.branch_id)
    
    def _format_header_row(self, ws: Worksheet) -> None:
        """Apply formatting to header row"""
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Freeze header row
        ws.freeze_panes = "A2"
        
        # Auto-fit columns
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # ========================================================================
    # PATIENT ID GENERATION
    # ========================================================================
    
    def _generate_patient_id(self, timestamp: Optional[datetime] = None) -> str:
        """
        Generate unique patient ID
        Format: {BRANCH_CODE}-{YYYYMMDD}-{SEQUENCE}
        
        Args:
            timestamp: Timestamp for ID generation (default: now)
        
        Returns:
            Unique patient ID
        """
        with self._id_counter_lock:
            if timestamp is None:
                timestamp = datetime.now()
            
            date_str = timestamp.strftime("%Y%m%d")
            
            # Get current file and count today's customers
            filepath = self.get_current_excel_file()
            
            with self.file_lock.acquire(filepath):
                wb = load_workbook(filepath)
                ws = wb.active
                
                # Count customers with same date prefix
                sequence = 1
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row[1]:  # Customer ID column
                        patient_id = str(row[1])
                        if patient_id.startswith(f"{self.config.BRANCH_CODE}-{date_str}"):
                            try:
                                seq_num = int(patient_id.split('-')[-1])
                                sequence = max(sequence, seq_num + 1)
                            except:
                                pass
            
            return f"{self.config.BRANCH_CODE}-{date_str}-{sequence:04d}"
    
    # ========================================================================
    # DATA VALIDATION
    # ========================================================================
    
    def _validate_patient_data(self, patient_data: Dict[str, Any]) -> None:
        """
        Validate patient data before saving
        
        Args:
            patient_data: Customer data dictionary
        
        Raises:
            DataValidationError: If validation fails
        """
        # Required fields
        required_fields = ['patient_name', 'age', 'gender', 'test_type', 'contact_number']
        for field in required_fields:
            if field not in patient_data or not patient_data[field]:
                raise DataValidationError(f"Missing required field: {field}", self.branch_id)
        
        # Name length
        if len(patient_data['patient_name']) > self.config.MAX_PATIENT_NAME_LENGTH:
            raise DataValidationError(
                f"Customer name exceeds maximum length of {self.config.MAX_PATIENT_NAME_LENGTH}",
                self.branch_id
            )
        
        # Age validation
        try:
            age = int(patient_data['age'])
            if age < 0 or age > 150:
                raise DataValidationError("Age must be between 0 and 150", self.branch_id)
        except ValueError:
            raise DataValidationError("Age must be a valid number", self.branch_id)
        
        # Gender validation
        if patient_data['gender'] not in self.config.VALID_GENDERS:
            raise DataValidationError(
                f"Gender must be one of: {', '.join(self.config.VALID_GENDERS)}",
                self.branch_id
            )
        
        # Status validation (if provided)
        if 'status' in patient_data and patient_data['status']:
            if patient_data['status'] not in self.config.VALID_STATUSES:
                raise DataValidationError(
                    f"Status must be one of: {', '.join(self.config.VALID_STATUSES)}",
                    self.branch_id
                )
        
        # Notes length (if provided)
        if 'notes' in patient_data and patient_data['notes']:
            if len(patient_data['notes']) > self.config.MAX_NOTES_LENGTH:
                raise DataValidationError(
                    f"Notes exceed maximum length of {self.config.MAX_NOTES_LENGTH}",
                    self.branch_id
                )
        
        # Contact number format (basic validation)
        contact = str(patient_data['contact_number']).strip()
        if not contact or len(contact) < 10:
            raise DataValidationError("Contact number must be at least 10 digits", self.branch_id)

# Continuation of DailyEntryManager class methods

    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    @log_operation("Add Customer Record")
    @retry_on_failure(max_attempts=3)
    def add_patient_record(self, patient_data: Dict[str, Any], created_by: str = "System") -> CustomerRecord:
        """
        Add a new patient record to the current month's Excel file
        
        Args:
            patient_data: Dictionary containing patient information
            created_by: Username of the person creating the record
        
        Returns:
            Created CustomerRecord object
        
        Raises:
            DataValidationError: If validation fails
            FileAccessError: If file operations fail
        """
        # Validate data
        self._validate_patient_data(patient_data)
        
        # Generate patient ID
        patient_id = self._generate_patient_id()
        
        # Create patient record
        record = CustomerRecord(
            patient_id=patient_id,
            patient_name=patient_data['patient_name'],
            age=int(patient_data['age']),
            gender=patient_data['gender'],
            test_type=patient_data['test_type'],
            referring_doctor=patient_data.get('referring_doctor', ''),
            status=patient_data.get('status', 'Pending'),
            contact_number=patient_data['contact_number'],
            notes=patient_data.get('notes', ''),
            branch_id=self.branch_id,
            created_by=created_by,
            timestamp=datetime.now(),
            last_updated=datetime.now(),
            is_archived=False
        )
        
        # Get current Excel file
        filepath = self.get_current_excel_file()
        
        # Backup before write
        self._create_backup(filepath)
        
        # Write to Excel
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath)
            ws = wb.active
            
            # Append row
            ws.append(record.to_excel_row())
            
            # Apply formatting to new row
            self._format_data_row(ws, ws.max_row)
            
            # Save workbook
            wb.save(filepath)
        
        # Invalidate cache
        if self.stats_cache:
            self.stats_cache.invalidate()
        
        self.logger.info(f"Added patient record: {patient_id}")
        return record
    
    def get_todays_customers(self) -> List[CustomerRecord]:
        """
        Get all patient records from today
        
        Returns:
            List of CustomerRecord objects from today
        """
        today = date.today()
        filepath = self.get_current_excel_file()
        
        records = []
        
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath, read_only=True)
            ws = wb.active
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:  # Skip empty rows
                    continue
                
                # Check if timestamp is today
                timestamp = row[0]
                if isinstance(timestamp, datetime):
                    record_date = timestamp.date()
                else:
                    try:
                        record_date = datetime.fromisoformat(str(timestamp)).date()
                    except:
                        continue
                
                if record_date == today:
                    try:
                        record = CustomerRecord.from_excel_row(list(row), self.branch_id)
                        records.append(record)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse row: {e}")
                        continue
            
            wb.close()
        
        return records
    
    def get_monthly_report(self, year: int, month: int) -> pd.DataFrame:
        """
        Get all records for a specific month
        
        Args:
            year: Year
            month: Month (1-12)
        
        Returns:
            Pandas DataFrame with monthly records
        """
        filepath = self.get_current_excel_file(year, month)
        
        if not os.path.exists(filepath):
            self.logger.warning(f"No data file found for {year}-{month:02d}")
            return pd.DataFrame()
        
        try:
            df = pd.read_excel(filepath)
            return df
        except Exception as e:
            raise FileAccessError(f"Failed to read monthly report: {str(e)}", self.branch_id)
    
    def get_yearly_report(self, year: int) -> pd.DataFrame:
        """
        Get all records for a specific year
        
        Args:
            year: Year
        
        Returns:
            Pandas DataFrame with yearly records
        """
        all_data = []
        
        for month in range(1, 13):
            try:
                monthly_df = self.get_monthly_report(year, month)
                if not monthly_df.empty:
                    all_data.append(monthly_df)
            except Exception as e:
                self.logger.debug(f"No data for {year}-{month:02d}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        yearly_df = pd.concat(all_data, ignore_index=True)
        return yearly_df
    
    def search_customers(self, search_term: str, date_range: Optional[Tuple[date, date]] = None) -> List[CustomerRecord]:
        """
        Search for customers across records
        
        Args:
            search_term: Search term (patient name, ID, contact number)
            date_range: Optional tuple of (start_date, end_date)
        
        Returns:
            List of matching CustomerRecord objects
        """
        search_term = search_term.lower().strip()
        results = []
        
        # Determine which files to search
        if date_range:
            start_date, end_date = date_range
            files_to_search = self._get_files_in_date_range(start_date, end_date)
        else:
            # Search current month by default
            files_to_search = [self.get_current_excel_file()]
        
        for filepath in files_to_search:
            if not os.path.exists(filepath):
                continue
            
            with self.file_lock.acquire(filepath):
                wb = load_workbook(filepath, read_only=True)
                ws = wb.active
                
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[0]:
                        continue
                    
                    # Search in patient ID, name, and contact number
                    patient_id = str(row[1]).lower() if row[1] else ""
                    patient_name = str(row[2]).lower() if row[2] else ""
                    contact = str(row[8]).lower() if row[8] else ""
                    
                    if (search_term in patient_id or 
                        search_term in patient_name or 
                        search_term in contact):
                        try:
                            record = CustomerRecord.from_excel_row(list(row), self.branch_id)
                            results.append(record)
                        except Exception as e:
                            self.logger.warning(f"Failed to parse search result row: {e}")
                            continue
                
                wb.close()
        
        return results
    
    @log_operation("Update Customer Status")
    @retry_on_failure(max_attempts=3)
    def update_patient_status(self, patient_id: str, new_status: str) -> bool:
        """
        Update patient status
        
        Args:
            patient_id: Customer ID to update
            new_status: New status value
        
        Returns:
            True if updated successfully
        
        Raises:
            CustomerNotFoundError: If patient not found
            DataValidationError: If status is invalid
        """
        # Validate status
        if new_status not in self.config.VALID_STATUSES:
            raise DataValidationError(
                f"Invalid status. Must be one of: {', '.join(self.config.VALID_STATUSES)}",
                self.branch_id
            )
        
        # Find the file containing this patient
        filepath, row_num = self._find_patient_row(patient_id)
        
        if not filepath:
            raise CustomerNotFoundError(f"Customer not found: {patient_id}", self.branch_id)
        
        # Backup before update
        self._create_backup(filepath)
        
        # Update the record
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath)
            ws = wb.active
            
            # Update status (column H) and last_updated (column M)
            ws.cell(row=row_num, column=8).value = new_status
            ws.cell(row=row_num, column=13).value = datetime.now()
            
            wb.save(filepath)
        
        # Invalidate cache
        if self.stats_cache:
            self.stats_cache.invalidate()
        
        self.logger.info(f"Updated status for patient {patient_id} to {new_status}")
        return True
    
    # ========================================================================
    # STATISTICS AND ANALYTICS
    # ========================================================================
    
    def get_branch_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive branch statistics
        
        Returns:
            Dictionary with statistics (today, this month, this year)
        """
        # Check cache first
        if self.stats_cache:
            cached = self.stats_cache.get('branch_stats')
            if cached:
                return cached
        
        today = date.today()
        
        # Today's statistics
        todays_customers = self.get_todays_customers()
        today_count = len(todays_customers)
        today_by_status = {}
        for patient in todays_customers:
            status = patient.status
            today_by_status[status] = today_by_status.get(status, 0) + 1
        
        # This month's statistics
        monthly_df = self.get_monthly_report(today.year, today.month)
        month_count = len(monthly_df) if not monthly_df.empty else 0
        
        # This year's statistics
        yearly_df = self.get_yearly_report(today.year)
        year_count = len(yearly_df) if not yearly_df.empty else 0
        
        stats = {
            'branch_id': self.branch_id,
            'branch_name': self.branch_name,
            'today': {
                'total_customers': today_count,
                'by_status': today_by_status,
                'date': today.isoformat()
            },
            'this_month': {
                'total_customers': month_count,
                'year': today.year,
                'month': today.month
            },
            'this_year': {
                'total_customers': year_count,
                'year': today.year
            },
            'generated_at': datetime.now().isoformat()
        }
        
        # Cache the results
        if self.stats_cache:
            self.stats_cache.set('branch_stats', stats)
        
        return stats
    
    @log_operation("Generate Daily Summary")
    def generate_daily_summary(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generate comprehensive daily summary report
        
        Args:
            target_date: Date for summary (default: today)
        
        Returns:
            Dictionary with daily summary data
        """
        if target_date is None:
            target_date = date.today()
        
        filepath = self.get_current_excel_file(target_date.year, target_date.month)
        
        if not os.path.exists(filepath):
            return {
                'date': target_date.isoformat(),
                'total_customers': 0,
                'by_status': {},
                'by_gender': {},
                'by_test_type': {},
                'message': 'No data available for this date'
            }
        
        customers = []
        
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath, read_only=True)
            ws = wb.active
            
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0]:
                    continue
                
                # Check if record is from target date
                timestamp = row[0]
                if isinstance(timestamp, datetime):
                    record_date = timestamp.date()
                else:
                    try:
                        record_date = datetime.fromisoformat(str(timestamp)).date()
                    except:
                        continue
                
                if record_date == target_date:
                    try:
                        record = CustomerRecord.from_excel_row(list(row), self.branch_id)
                        customers.append(record)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse row in daily summary: {e}")
                        continue
            
            wb.close()
        
        # Compile statistics
        by_status = {}
        by_gender = {}
        by_test_type = {}
        
        for patient in customers:
            # By status
            by_status[patient.status] = by_status.get(patient.status, 0) + 1
            
            # By gender
            by_gender[patient.gender] = by_gender.get(patient.gender, 0) + 1
            
            # By test type
            by_test_type[patient.test_type] = by_test_type.get(patient.test_type, 0) + 1
        
        summary = {
            'date': target_date.isoformat(),
            'branch_id': self.branch_id,
            'branch_name': self.branch_name,
            'total_customers': len(customers),
            'by_status': by_status,
            'by_gender': by_gender,
            'by_test_type': by_test_type,
            'generated_at': datetime.now().isoformat()
        }
        
        return summary
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _find_patient_row(self, patient_id: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Find the Excel file and row number for a patient ID
        
        Args:
            patient_id: Customer ID to find
        
        Returns:
            Tuple of (filepath, row_number) or (None, None) if not found
        """
        # Extract date from patient ID to narrow search
        try:
            parts = patient_id.split('-')
            if len(parts) >= 2:
                date_str = parts[1]  # YYYYMMDD
                year = int(date_str[:4])
                month = int(date_str[4:6])
                filepath = self.get_current_excel_file(year, month)
                
                if os.path.exists(filepath):
                    with self.file_lock.acquire(filepath):
                        wb = load_workbook(filepath, read_only=True)
                        ws = wb.active
                        
                        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                            if row[1] == patient_id:
                                wb.close()
                                return filepath, idx
                        
                        wb.close()
        except Exception as e:
            self.logger.debug(f"Error in _find_patient_row: {e}")
        
        return None, None
    
    def _get_files_in_date_range(self, start_date: date, end_date: date) -> List[str]:
        """
        Get list of Excel files covering a date range
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            List of file paths
        """
        files = []
        current = start_date.replace(day=1)
        
        while current <= end_date:
            filepath = self.get_current_excel_file(current.year, current.month)
            if os.path.exists(filepath):
                files.append(filepath)
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return files
    
    def _format_data_row(self, ws: Worksheet, row_num: int) -> None:
        """Apply formatting to a data row"""
        # Status-based color coding
        status_cell = ws.cell(row=row_num, column=8)
        status = status_cell.value
        
        if status == "Completed":
            fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        elif status == "In Progress":
            fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        elif status == "Cancelled":
            fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        else:
            fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        
        status_cell.fill = fill

# Continuation of DailyEntryManager class methods

    # ========================================================================
    # BACKUP AND ARCHIVING
    # ========================================================================
    
    def _create_backup(self, filepath: str) -> str:
        """
        Create backup of Excel file before modification
        
        Args:
            filepath: Path to file to backup
        
        Returns:
            Path to backup file
        """
        if not os.path.exists(filepath):
            return ""
        
        backup_dir = self.config.get_full_path(self.config.BACKUP_FOLDER)
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = os.path.basename(filepath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{os.path.splitext(filename)[0]}_backup_{timestamp}.xlsx"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            shutil.copy2(filepath, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            return ""
    
    @log_operation("Archive Old Data")
    def archive_old_data(self, months_to_keep: int = 3) -> Dict[str, Any]:
        """
        Move old monthly files to archive folder
        
        Args:
            months_to_keep: Number of recent months to keep in main folder
        
        Returns:
            Dictionary with archiving results
        """
        archive_dir = self.config.get_full_path(self.config.ARCHIVE_FOLDER)
        base_dir = self.config.BASE_DATA_PATH
        
        archived_files = []
        errors = []
        
        # Get current date
        now = datetime.now()
        cutoff_date = now - timedelta(days=months_to_keep * 30)
        
        # Find Excel files in base directory
        for filename in os.listdir(base_dir):
            if not filename.endswith('.xlsx') or not filename.startswith('Daily_Customer_Log'):
                continue
            
            filepath = os.path.join(base_dir, filename)
            
            # Extract year and month from filename
            try:
                parts = filename.split('_')
                year = int(parts[-2])
                month = int(parts[-1].replace('.xlsx', ''))
                
                file_date = datetime(year, month, 1)
                
                if file_date < cutoff_date:
                    # Archive this file
                    year_month_dir = os.path.join(archive_dir, str(year), f"{month:02d}")
                    os.makedirs(year_month_dir, exist_ok=True)
                    
                    dest_path = os.path.join(year_month_dir, filename)
                    shutil.move(filepath, dest_path)
                    
                    archived_files.append({
                        'filename': filename,
                        'year': year,
                        'month': month,
                        'archived_to': dest_path
                    })
                    
                    self.logger.info(f"Archived file: {filename} to {dest_path}")
            
            except Exception as e:
                errors.append({
                    'filename': filename,
                    'error': str(e)
                })
                self.logger.error(f"Failed to archive {filename}: {e}")
        
        return {
            'archived_count': len(archived_files),
            'archived_files': archived_files,
            'errors': errors,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    # ========================================================================
    # BRANCH TRANSFER
    # ========================================================================
    
    @log_operation("Transfer Customer Between Branches")
    def transfer_between_branches(self, patient_id: str, target_branch_id: str, 
                                  target_manager: 'DailyEntryManager') -> Dict[str, Any]:
        """
        Transfer a patient record to another branch
        
        Args:
            patient_id: Customer ID to transfer
            target_branch_id: Target branch ID
            target_manager: DailyEntryManager instance for target branch
        
        Returns:
            Dictionary with transfer results
        
        Raises:
            CustomerNotFoundError: If patient not found
            DailyEntryError: If transfer fails
        """
        # Find patient in source branch
        filepath, row_num = self._find_patient_row(patient_id)
        
        if not filepath:
            raise CustomerNotFoundError(f"Customer not found: {patient_id}", self.branch_id)
        
        # Read patient data
        patient_record = None
        
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath, read_only=True)
            ws = wb.active
            
            row_data = list(ws[row_num])
            row_values = [cell.value for cell in row_data]
            patient_record = CustomerRecord.from_excel_row(row_values, self.branch_id)
            
            wb.close()
        
        if not patient_record:
            raise DailyEntryError("Failed to read patient record", "DE_TRANSFER_ERROR", self.branch_id)
        
        # Create new record in target branch
        patient_data = {
            'patient_name': patient_record.patient_name,
            'age': patient_record.age,
            'gender': patient_record.gender,
            'test_type': patient_record.test_type,
            'referring_doctor': patient_record.referring_doctor,
            'status': patient_record.status,
            'contact_number': patient_record.contact_number,
            'notes': f"[Transferred from {self.branch_id}] {patient_record.notes}"
        }
        
        new_record = target_manager.add_patient_record(
            patient_data,
            created_by=f"Transfer from {self.branch_id}"
        )
        
        # Mark original record as archived
        self.update_patient_status(patient_id, "Transferred")
        
        # Update archived flag
        with self.file_lock.acquire(filepath):
            wb = load_workbook(filepath)
            ws = wb.active
            ws.cell(row=row_num, column=14).value = True  # is_archived column
            ws.cell(row=row_num, column=10).value = f"Transferred to {target_branch_id}"  # notes
            wb.save(filepath)
        
        transfer_result = {
            'success': True,
            'source_branch': self.branch_id,
            'target_branch': target_branch_id,
            'original_patient_id': patient_id,
            'new_patient_id': new_record.patient_id,
            'transferred_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"Transferred patient {patient_id} to branch {target_branch_id}")
        
        return transfer_result
    
    # ========================================================================
    # EXPORT FUNCTIONS
    # ========================================================================
    
    def export_to_csv(self, data: pd.DataFrame, filename: str) -> str:
        """
        Export data to CSV file
        
        Args:
            data: DataFrame to export
            filename: Output filename
        
        Returns:
            Path to exported file
        """
        export_dir = self.config.get_full_path(self.config.EXPORTS_FOLDER)
        os.makedirs(export_dir, exist_ok=True)
        
        filepath = os.path.join(export_dir, filename)
        
        try:
            data.to_csv(filepath, index=False)
            self.logger.info(f"Exported to CSV: {filepath}")
            return filepath
        except Exception as e:
            raise FileAccessError(f"Failed to export CSV: {str(e)}", self.branch_id)
    
    def export_to_pdf(self, data: pd.DataFrame, filename: str, title: str = "Customer Order") -> str:
        """
        Export data to PDF file
        
        Args:
            data: DataFrame to export
            filename: Output filename
            title: Order title
        
        Returns:
            Path to exported file
        """
        if not PDF_AVAILABLE:
            raise DailyEntryError(
                "PDF export not available. Install reportlab: pip install reportlab",
                "DE_PDF_ERROR",
                self.branch_id
            )
        
        export_dir = self.config.get_full_path(self.config.EXPORTS_FOLDER)
        os.makedirs(export_dir, exist_ok=True)
        
        filepath = os.path.join(export_dir, filename)
        
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            title_para = Paragraph(f"<b>{title}</b><br/>{self.branch_name}", styles['Title'])
            elements.append(title_para)
            
            # Convert DataFrame to table data
            table_data = [data.columns.tolist()] + data.values.tolist()
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            self.logger.info(f"Exported to PDF: {filepath}")
            return filepath
            
        except Exception as e:
            raise FileAccessError(f"Failed to export PDF: {str(e)}", self.branch_id)
    
    @log_operation("Export Daily Order")
    def export_daily_report(self, target_date: Optional[date] = None, 
                           format: str = 'csv') -> str:
        """
        Export daily report to file
        
        Args:
            target_date: Date for report (default: today)
            format: Export format ('csv' or 'pdf')
        
        Returns:
            Path to exported file
        """
        if target_date is None:
            target_date = date.today()
        
        # Get daily data
        summary = self.generate_daily_summary(target_date)
        
        # Get patient records
        filepath = self.get_current_excel_file(target_date.year, target_date.month)
        
        if not os.path.exists(filepath):
            raise FileAccessError(f"No data available for {target_date}", self.branch_id)
        
        # Read data
        df = pd.read_excel(filepath)
        
        # Filter for target date
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df_filtered = df[df['Timestamp'].dt.date == target_date]
        
        # Generate filename
        filename = f"Daily_Order_{self.branch_id}_{target_date.strftime('%Y%m%d')}.{format}"
        
        # Export based on format
        if format.lower() == 'csv':
            return self.export_to_csv(df_filtered, filename)
        elif format.lower() == 'pdf':
            title = f"Daily Order - {target_date.strftime('%Y-%m-%d')}"
            return self.export_to_pdf(df_filtered, filename, title)
        else:
            raise DataValidationError(f"Unsupported export format: {format}", self.branch_id)
    
    @log_operation("Export Monthly Order")
    def export_monthly_report(self, year: int, month: int, format: str = 'csv') -> str:
        """
        Export monthly report to file
        
        Args:
            year: Year
            month: Month
            format: Export format ('csv' or 'pdf')
        
        Returns:
            Path to exported file
        """
        df = self.get_monthly_report(year, month)
        
        if df.empty:
            raise FileAccessError(f"No data available for {year}-{month:02d}", self.branch_id)
        
        filename = f"Monthly_Order_{self.branch_id}_{year}_{month:02d}.{format}"
        
        if format.lower() == 'csv':
            return self.export_to_csv(df, filename)
        elif format.lower() == 'pdf':
            title = f"Monthly Order - {year}-{month:02d}"
            return self.export_to_pdf(df, filename, title)
        else:
            raise DataValidationError(f"Unsupported export format: {format}", self.branch_id)
    
    @log_operation("Export Yearly Order")
    def export_yearly_report(self, year: int, format: str = 'csv') -> str:
        """
        Export yearly report to file
        
        Args:
            year: Year
            format: Export format ('csv' or 'pdf')
        
        Returns:
            Path to exported file
        """
        df = self.get_yearly_report(year)
        
        if df.empty:
            raise FileAccessError(f"No data available for {year}", self.branch_id)
        
        filename = f"Yearly_Order_{self.branch_id}_{year}.{format}"
        
        if format.lower() == 'csv':
            return self.export_to_csv(df, filename)
        elif format.lower() == 'pdf':
            title = f"Yearly Order - {year}"
            return self.export_to_pdf(df, filename, title)
        else:
            raise DataValidationError(f"Unsupported export format: {format}", self.branch_id)


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_daily_entry_manager(branch_id: str = "BRANCH_001",
                               branch_name: str = "City Center Lab",
                               branch_code: str = "CCL",
                               base_path: Optional[str] = None) -> DailyEntryManager:
    """
    Factory function to create DailyEntryManager instance
    
    Args:
        branch_id: Unique branch identifier
        branch_name: Branch display name
        branch_code: Short branch code for patient IDs
        base_path: Base data path (optional)
    
    Returns:
        Configured DailyEntryManager instance
    """
    config = BranchConfig(
        BRANCH_ID=branch_id,
        BRANCH_NAME=branch_name,
        BRANCH_CODE=branch_code,
        BASE_DATA_PATH=base_path or f"C:/ERP_Data/{branch_id}/"
    )
    
    manager = DailyEntryManager(config)
    manager.initialize_branch_structure()
    
    return manager


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage of DailyEntryManager
    """
    
    # Create manager for a branch
    manager = create_daily_entry_manager(
        branch_id="BRANCH_001",
        branch_name="City Center Lab",
        branch_code="CCL"
    )
    
    # Add a patient record
    patient_data = {
        'patient_name': 'John Doe',
        'age': 35,
        'gender': 'Male',
        'test_type': 'Blood MenuItem',
        'referring_doctor': 'Dr. Smith',
        'status': 'Pending',
        'contact_number': '1234567890',
        'notes': 'Routine checkup'
    }
    
    try:
        record = manager.add_patient_record(patient_data, created_by="Admin")
        print(f"Added patient: {record.patient_id}")
        
        # Get today's customers
        todays_customers = manager.get_todays_customers()
        print(f"Today's customers: {len(todays_customers)}")
        
        # Get branch statistics
        stats = manager.get_branch_statistics()
        print(f"Branch statistics: {stats}")
        
        # Generate daily summary
        summary = manager.generate_daily_summary()
        print(f"Daily summary: {summary}")
        
        # Export daily report
        csv_path = manager.export_daily_report(format='csv')
        print(f"Exported daily report to: {csv_path}")
        
    except DailyEntryError as e:
        print(f"Error: {e}")
