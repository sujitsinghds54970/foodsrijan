import React from 'react';
import { Button, Tooltip, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Save, FileDownload, FileUpload, Add, Receipt, FilterList, Search } from '@mui/icons-material';

interface ToolbarProps {
  onSave: () => void;
  onExportExcel: () => void;
  onImportExcel: (file: File) => void;
  onAddCustomer: () => void;
  onGenerateInvoice: () => void;
  onFilter: (filter: string) => void;
  fontSize: string;
  onFontSizeChange: (size: string) => void;
  selectedRowsCount: number;
}

const DailyEntryGridToolbar: React.FC<ToolbarProps> = ({
  onSave,
  onExportExcel,
  onImportExcel,
  onAddCustomer,
  onGenerateInvoice,
  onFilter,
  fontSize,
  onFontSizeChange,
  selectedRowsCount
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-white border-b border-gray-200 rounded-lg shadow-sm">
      <div className="flex items-center gap-2">
        <Tooltip title="Save all changes">
          <Button variant="contained" startIcon={<Save />} onClick={onSave}>
            Save All
          </Button>
        </Tooltip>
        <Tooltip title="Add New Customer">
          <Button variant="outlined" startIcon={<Add />} onClick={onAddCustomer}>
            New Customer
          </Button>
        </Tooltip>
        {selectedRowsCount > 0 && (
          <Tooltip title={`Generate invoice for ${selectedRowsCount} customers`}>
            <Button variant="contained" color="primary" startIcon={<Receipt />} onClick={onGenerateInvoice}>
              Generate Bills ({selectedRowsCount})
            </Button>
          </Tooltip>
        )}
      </div>

      <div className="flex items-center gap-2">
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>Font Size</InputLabel>
          <Select
            value={fontSize}
            label="Font Size"
            onChange={(e) => onFontSizeChange(e.target.value)}
          >
            <MenuItem value="small">Small</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="large">Large</MenuItem>
          </Select>
        </FormControl>

        <Tooltip title="Filter">
          <Button variant="outlined" startIcon={<FilterList />}>
            Filters
          </Button>
        </Tooltip>

        <Tooltip title="Export Excel">
          <Button variant="outlined" startIcon={<FileDownload />} onClick={onExportExcel}>
            Export
          </Button>
        </Tooltip>

        <label htmlFor="excel-upload">
          <Button component="span" variant="outlined" startIcon={<FileUpload />}>
            Import
          </Button>
          <input
            id="excel-upload"
            type="file"
            accept=".xlsx,.xls"
            hidden
            onChange={(e) => e.target.files && onImportExcel(e.target.files![0])}
          />
        </label>
      </div>
    </div>
  );
};

export default DailyEntryGridToolbar;

