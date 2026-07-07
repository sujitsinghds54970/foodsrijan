import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import DailyEntryGridToolbar from './DailyEntryGridToolbar';
import AddPatientModal from './AddPatientModal';
import { dailyEntryService } from '../../services/dailyEntryService';
import { DailyEntryRow, GridApiResponse, Patient } from '../../types/daily-entry';
import { toast } from 'react-hot-toast';
import { Card, CardContent, Typography, Chip, Box } from '@mui/material';
import { TrendingUp, People, AttachMoney } from '@mui/icons-material';

const DailyEntry: React.FC = () => {
  const { user } = useAuth();
  const gridRef = useRef<AgGridReact>(null);
  const [rowData, setRowData] = useState<DailyEntryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRows, setSelectedRows] = useState<DailyEntryRow[]>([]);
  const [fontSize, setFontSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [summary, setSummary] = useState({
    total_patients: 0,
    total_revenue: 0,
    pending_amount: 0,
  });
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0]);

  // Column definitions for AG-Grid (Excel-like)
  const columnDefs = useMemo(() => [
    {
      headerName: 'Patient',
      field: 'patient_name',
      editable: true,
      filter: 'agTextColumnFilter',
      cellRenderer: (params: any) => (
        <strong>{params.value}</strong>
      ),
      width: 150,
    },
    {
      headerName: 'Phone',
      field: 'patient_phone',
      editable: true,
      filter: 'agTextColumnFilter',
      width: 130,
    },
    {
      headerName: 'Doctor',
      field: 'doctor_name',
      editable: true,
      filter: 'agTextColumnFilter',
      width: 150,
    },
    {
      headerName: 'Date',
      field: 'visit_date',
      editable: true,
      filter: 'agDateColumnFilter',
      cellEditor: 'agDateCellEditor',
      width: 120,
    },
    {
      headerName: 'Consult Fee',
      field: 'consultation_fee',
      editable: true,
      filter: 'agNumberColumnFilter',
      cellEditor: 'agNumberCellEditor',
      valueFormatter: (params: any) => `₹${params.value?.toLocaleString() || 0}`,
      cellStyle: { textAlign: 'right' },
      width: 120,
    },
    {
      headerName: 'Test Fee',
      field: 'test_fee',
      editable: true,
      filter: 'agNumberColumnFilter',
      cellEditor: 'agNumberCellEditor',
      valueFormatter: (params: any) => `₹${params.value?.toLocaleString() || 0}`,
      cellStyle: { textAlign: 'right' },
      width: 120,
    },
    {
      headerName: 'Total',
      field: 'total_amount',
      editable: false,
      valueGetter: 'data.consultation_fee + data.test_fee',
      valueFormatter: (params: any) => `₹${params.value?.toLocaleString() || 0}`,
      cellStyle: { 
        textAlign: 'right',
        fontWeight: 'bold',
      },
      aggFunc: 'sum',
      width: 120,
      pinned: 'right' as const,
    },
    {
      headerName: 'Test Type',
      field: 'test_type',
      editable: true,
      filter: 'agTextColumnFilter',
      flex: 1,
    },
    {
      headerName: 'Status',
      field: 'payment_status',
      editable: true,
      cellRenderer: (params: any) => {
        const status = params.value;
        const color = status === 'paid' ? 'success' : status === 'pending' ? 'warning' : 'error';
        return (
          <Chip 
            label={status} 
            color={color as any} 
            size="small"
          />
        );
      },
      cellStyle: { justifyContent: 'center' },
      width: 110,
      pinned: 'right' as const,
    },
    {
      headerName: 'Notes',
      field: 'notes',
      editable: true,
      flex: 1,
      wrapText: true,
      autoHeight: true,
    },
    {
      headerName: 'History',
      field: 'history_count',
      editable: false,
      valueFormatter: (params: any) => `${params.value || 0} visits`,
      width: 100,
    },
  ], []);

  // Default column state (Excel-like features)
  const defaultColDef = useMemo(() => ({
    sortable: true,
    resizable: true,
    floatingFilter: true,
    flex: 1,
    cellStyle: { fontSize: fontSize === 'small' ? '12px' : fontSize === 'medium' ? '14px' : '16px' },
  }), [fontSize]);

  // Load data
  const loadGridData = useCallback(async () => {
    if (!user?.branch_id) return;
    try {
      setLoading(true);
      const data = await dailyEntryService.getGridData(dateFilter, user.branch_id);
      setRowData(data.entries);
      setSummary(data.summary);
    } catch (error) {
      toast.error('Failed to load data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [dateFilter, user?.branch_id]);

  useEffect(() => {
    loadGridData();
  }, [loadGridData]);

  // Grid event handlers
  const onSelectionChanged = useCallback(() => {
    const selected = gridRef.current?.api.getSelectedRows() || [];
    setSelectedRows(selected as DailyEntryRow[]);
  }, []);

  const onCellValueChanged = useCallback((event: any) => {
    // Auto-calculate total
    if (['consultation_fee', 'test_fee'].includes(event.colDef.field)) {
      const row = event.data;
      row.total_amount = (row.consultation_fee || 0) + (row.test_fee || 0);
      gridRef.current?.api.refreshCells({ rowNodes: [event.node], force: true });
    }
  }, []);

  // Toolbar handlers
const handleSave = useCallback(async () => {
    toast.loading('Saving changes...', { id: 'save' });
    try {
      gridRef.current?.api.stopEditing();
      const updates = rowData.filter(row => row.id).map(row => ({ 
        id: row.id!, 
        patient_id: row.patient_id,
        doctor_id: row.doctor_id,
        visit_date: row.visit_date,
        consultation_fee: row.consultation_fee,
        test_fee: row.test_fee,
        test_type: row.test_type,
        notes: row.notes,
        payment_status: row.payment_status
      }));
      await dailyEntryService.bulkUpdate(updates as any);
      toast.success('Saved!', { id: 'save' });
      loadGridData();
    } catch (error) {
      toast.error('Save failed', { id: 'save' });
    }
  }, [rowData, loadGridData]);

  const handleGenerateInvoice = useCallback(async () => {
    if (selectedRows.length === 0) {
      toast.error('Select rows to generate invoice');
      return;
    }
    const ids = selectedRows.map(r => r.id!).filter(Boolean);
    try {
      const invoice = await dailyEntryService.createInvoice(ids);
      toast.success(`Invoice ${invoice.invoice_number} created!`);
    } catch (error) {
      toast.error('Invoice creation failed');
    }
  }, [selectedRows]);

  const handleExportExcel = useCallback(() => {
    dailyEntryService.exportExcel(dateFilter, dateFilter);
  }, [dateFilter]);

  const handleImportExcel = useCallback((file: File) => {
    toast('Import not implemented yet');
  }, []);

  const [addPatientOpen, setAddPatientOpen] = useState(false);

  const handleAddPatient = useCallback(() => {
    setAddPatientOpen(true);
  }, []);

  const handlePatientAdded = useCallback((newPatient: Patient) => {
    toast.success(`Added ${newPatient.first_name} ${newPatient.last_name}`);
    loadGridData();
  }, [loadGridData]);

  const handlePatientClose = useCallback(() => {
    setAddPatientOpen(false);
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading Excel Grid...</div>;
  }

  return (
    <div className="space-y-6 h-screen flex flex-col">
      {/* Header */}
      <Card>
        <CardContent className="pb-0">
          <Typography variant="h4" gutterBottom>
            Daily Entry Sheet (Branch: {user?.branch_id || 'Main'})
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Excel-like spreadsheet for branch admins. Edit cells directly, auto-calculations, bill generation.
          </Typography>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="text-center">
            <People color="primary" sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4">{summary.total_patients}</Typography>
            <Typography variant="body2" color="text.secondary">Patients</Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <AttachMoney color="success" sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4">₹{summary.total_revenue.toLocaleString()}</Typography>
            <Typography variant="body2" color="text.secondary">Revenue</Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <TrendingUp color="warning" sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h4">₹{summary.pending_amount.toLocaleString()}</Typography>
            <Typography variant="body2" color="text.secondary">Pending</Typography>
          </CardContent>
        </Card>
      </div>

      {/* Toolbar */}
      <DailyEntryGridToolbar
        onSave={handleSave}
        onExportExcel={handleExportExcel}
        onImportExcel={handleImportExcel}
        onAddPatient={handleAddPatient}
        onGenerateInvoice={handleGenerateInvoice}
        onFilter={() => {}} // TBD
        fontSize={fontSize}
        onFontSizeChange={(size) => setFontSize(size as any)}
        selectedRowsCount={selectedRows.length}
      />

      {/* AG-Grid */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="ag-theme-alpine h-full" style={{ height: '600px' }}>
          <AgGridReact
            ref={gridRef}
            rowData={rowData}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            rowSelection="multiple"
            onSelectionChanged={onSelectionChanged}
            onCellValueChanged={onCellValueChanged}
            animateRows={true}
            suppressRowClickSelection={true}
            enableRangeSelection={true}
            enableCellTextSelection={true}
            suppressMovableColumns={false}
            suppressMenuHide={false}
            pagination={false}
          />
        </div>
      </div>
    </div>
  );
};

export default DailyEntry;

