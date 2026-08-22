import React, { useState, useEffect } from 'react';
import {
  Box, Container, Grid, Paper, Typography, Card, CardContent,
  Button, Chip, IconButton, List, ListItem, ListItemText,
  ListItemIcon, Divider, Badge, Avatar, LinearProgress, Tab, Tabs,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, MenuItem, Dialog, DialogTitle, DialogContent,
  DialogActions, Snackbar, Alert
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Assignment as AssignmentIcon,
  Person as PersonIcon,
  Event as EventIcon,
  Description as DescriptionIcon,
  TrendingUp as TrendingUpIcon,
  AccessTime as AccessTimeIcon,
  CheckCircle as CheckCircleIcon,
  Pending as PendingIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import axios from 'axios';

interface StaffDashboardProps {
  doctorId: number;
}

interface Order {
  id: number;
  distribution_id: string;
  patient_name: string;
  report_type: string;
  report_name: string;
  delivery_status: string;
  created_at: string;
  viewed_at?: string;
}

interface StatCard {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  trend?: number;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function StaffDashboard({ doctorId }: StaffDashboardProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [orders, setOrders] = useState<Order[]>([]);
  const [statistics, setStatistics] = useState({
    totalOrders: 0,
    unreadOrders: 0,
    thisMonth: 0,
    urgentOrders: 0
  });
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  useEffect(() => {
    fetchDashboardData();
  }, [doctorId]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const API_BASE = window.location.origin;
      const [ordersRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE}/api/orders/pending-for-doctor/${doctorId}`),
        axios.get(`${API_BASE}/api/staff/${doctorId}/portal-dashboard`)
      ]);

      setOrders(ordersRes.data.orders || []);
      setStatistics({
        totalOrders: statsRes.data.statistics?.total_orders_received || 0,
        unreadOrders: statsRes.data.statistics?.unread_orders || 0,
        thisMonth: statsRes.data.statistics?.orders_this_month || 0,
        urgentOrders: 0
      });
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setSnackbar({ open: true, message: 'Failed to load dashboard data', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleViewOrder = async (report: Order) => {
    setSelectedOrder(report);
    setViewDialogOpen(true);

    try {
      const API_BASE = window.location.origin;
      await axios.post(`${API_BASE}/api/orders/${report.id}/acknowledge`, {
        action: 'view'
      });
      fetchDashboardData();
    } catch (error) {
      console.error('Error acknowledging report:', error);
    }
  };

  const handleDownloadOrder = async (reportId: number) => {
    try {
      const API_BASE = window.location.origin;
      const response = await axios.get(`${API_BASE}/api/orders/distribution/${reportId}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report-${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      await axios.post(`${API_BASE}/api/orders/${reportId}/acknowledge`, {
        action: 'download'
      });
      fetchDashboardData();
    } catch (error) {
      console.error('Error downloading report:', error);
      setSnackbar({ open: true, message: 'Failed to download report', severity: 'error' });
    }
  };

  const statCards: StatCard[] = [
    {
      title: 'Total Orders',
      value: statistics.totalOrders,
      icon: <DescriptionIcon />,
      color: '#3b82f6',
      trend: 12
    },
    {
      title: 'Unread Orders',
      value: statistics.unreadOrders,
      icon: <PendingIcon />,
      color: '#f59e0b'
    },
    {
      title: 'This Month',
      value: statistics.thisMonth,
      icon: <TrendingUpIcon />,
      color: '#10b981',
      trend: 8
    },
    {
      title: 'Urgent',
      value: statistics.urgentOrders,
      icon: <NotificationsIcon />,
      color: '#ef4444'
    }
  ];

  const reportTypeData = [
    { name: 'Blood MenuItem', value: 45 },
    { name: 'X-Ray', value: 20 },
    { name: 'MRI', value: 15 },
    { name: 'CT Scan', value: 12 },
    { name: 'Ultrasound', value: 8 }
  ];

  const weeklyActivity = [
    { day: 'Mon', orders: 12 },
    { day: 'Tue', orders: 19 },
    { day: 'Wed', orders: 15 },
    { day: 'Thu', orders: 22 },
    { day: 'Fri', orders: 18 },
    { day: 'Sat', orders: 8 },
    { day: 'Sun', orders: 3 }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'read': return 'success';
      case 'delivered': return 'info';
      case 'sent': return 'warning';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 4 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>Loading dashboard...</Typography>
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Staff Portal Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Welcome back! Here's your diagnostic report overview.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Badge badgeContent={statistics.unreadOrders} color="error">
            <IconButton color="primary">
              <NotificationsIcon />
            </IconButton>
          </Badge>
          <Button variant="contained" startIcon={<PersonIcon />}>
            My Profile
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" variant="body2" gutterBottom>
                      {card.title}
                    </Typography>
                    <Typography variant="h4" fontWeight="bold">
                      {card.value}
                    </Typography>
                    {card.trend && (
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        <TrendingUpIcon sx={{ fontSize: 16, color: 'success.main', mr: 0.5 }} />
                        <Typography variant="caption" color="success.main">
                          +{card.trend}% from last week
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  <Avatar sx={{ bgcolor: card.color, width: 56, height: 56 }}>
                    {card.icon}
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Weekly Order Activity
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={weeklyActivity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="orders" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Orders by Type
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={reportTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {reportTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Orders Section */}
      <Paper sx={{ mb: 4 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
            <Tab label={`Pending Orders (${statistics.unreadOrders})`} />
            <Tab label="All Orders" />
            <Tab label="Recent Activity" />
          </Tabs>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Order ID</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>Order Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Date</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      No pending orders
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                orders.slice(0, 10).map((report) => (
                  <TableRow key={report.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {report.distribution_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ width: 32, height: 32, mr: 1, bgcolor: 'primary.main' }}>
                          {report.patient_name?.charAt(0) || 'P'}
                        </Avatar>
                        <Typography variant="body2">
                          {report.patient_name || 'Unknown'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={report.report_type}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={report.delivery_status}
                        size="small"
                        color={getStatusColor(report.delivery_status)}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(report.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleViewOrder(report)}
                        title="View Order"
                      >
                        <VisibilityIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="success"
                        onClick={() => handleDownloadOrder(report.id)}
                        title="Download Order"
                      >
                        <DownloadIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Quick Actions */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <AssignmentIcon />
                </Avatar>
                <Typography variant="h6">Customer History</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                View complete patient history and previous orders.
              </Typography>
              <Button variant="outlined" fullWidth>
                View History
              </Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                  <EventIcon />
                </Avatar>
                <Typography variant="h6">Appointments</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                View and manage your upcoming appointments.
              </Typography>
              <Button variant="outlined" fullWidth>
                View Schedule
              </Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'info.main', mr: 2 }}>
                  <DescriptionIcon />
                </Avatar>
                <Typography variant="h6">MenuItem Catalog</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Browse available diagnostic menu_items and packages.
              </Typography>
              <Button variant="outlined" fullWidth>
                Browse MenuItems
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* View Order Dialog */}
      <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Order Details
          {selectedOrder && (
            <Chip
              label={selectedOrder.delivery_status}
              size="small"
              color={getStatusColor(selectedOrder.delivery_status)}
              sx={{ ml: 2 }}
            />
          )}
        </DialogTitle>
        <DialogContent dividers>
          {selectedOrder && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Order ID
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedOrder.distribution_id}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Order Type
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedOrder.report_name}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Customer
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedOrder.patient_name}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Date
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {new Date(selectedOrder.created_at).toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownloadOrder(selectedOrder.id)}
                  >
                    Download Order
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<VisibilityIcon />}
                    onClick={() => {
                      window.open(`/orders/view/${selectedOrder.id}`, '_blank');
                    }}
                  >
                    View Online
                  </Button>
                </Box>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}

