import axios from 'axios';
import { GridApiResponse, DailyEntryRow } from '../types/daily-entry';
import { toast } from 'react-hot-toast';

const API_BASE = '/api';

export const dailyEntryService = {
  async getGridData(date: string, branchId: number): Promise<GridApiResponse> {
    const res = await axios.get(`${API_BASE}/daily-entries/grid`, {
      params: { date, branch_id: branchId }
    });
    return res.data;
  },

  async bulkUpdate(updates: Partial<DailyEntryRow>[]): Promise<void> {
    await axios.put(`${API_BASE}/daily-entries/bulk`, { updates });
    toast.success('Changes saved successfully!');
  },

  async createInvoice(entryIds: number[]): Promise<any> {
    const res = await axios.post(`${API_BASE}/daily-entries/invoice`, { entry_ids: entryIds });
    return res.data;
  },

  async exportExcel(startDate: string, endDate: string): Promise<void> {
    const res = await axios.get(`${API_BASE}/export/daily-entries`, {
      params: { start_date: startDate, end_date: endDate, format: 'excel' },
      responseType: 'blob'
    });
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `daily-entries-${startDate}_to_${endDate}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  }
};

