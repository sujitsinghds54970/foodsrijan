import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { Customer } from '../../types/daily-entry';

interface AddCustomerModalProps {
  open: boolean;
  onClose: () => void;
  onCustomerAdded: (patient: Customer) => void;
  branchId: number;
}

interface CustomerFormData {
  first_name: string;
  last_name: string;
  phone: string;
  date_of_birth?: string;
  gender: 'male' | 'female' | 'other';
  address?: string;
}

const AddCustomerModal: React.FC<AddCustomerModalProps> = ({
  open,
  onClose,
  onCustomerAdded,
  branchId,
}) => {
  const { control, handleSubmit, reset, formState: { errors } } = useForm<CustomerFormData>({
    defaultValues: {
      first_name: '',
      last_name: '',
      phone: '',
      gender: 'male',
    },
  });
  const [loading, setLoading] = useState(false);

  const onSubmit = async (data: CustomerFormData) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/customers', {
        ...data,
        branch_id: branchId,
      });
      onCustomerAdded(response.data);
      toast.success('Customer added successfully!');
      reset();
      onClose();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add New Customer (Daily Entry)</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Controller
            name="first_name"
            control={control}
            rules={{ required: 'First name required' }}
            render={({ field }) => (
              <TextField
                {...field}
                label="First Name"
                fullWidth
                margin="normal"
                error={!!errors.first_name}
                helperText={errors.first_name?.message}
              />
            )}
          />
          <Controller
            name="last_name"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Last Name"
                fullWidth
                margin="normal"
              />
            )}
          />
          <Controller
            name="phone"
            control={control}
            rules={{ required: 'Phone required', minLength: { value: 10, message: '10 digits min' } }}
            render={({ field }) => (
              <TextField
                {...field}
                label="Phone"
                fullWidth
                margin="normal"
                error={!!errors.phone}
                helperText={errors.phone?.message}
              />
            )}
          />
          <Controller
            name="gender"
            control={control}
            render={({ field }) => (
              <TextField
                select
                {...field}
                label="Gender"
                fullWidth
                margin="normal"
              >
                <MenuItem value="male">Male</MenuItem>
                <MenuItem value="female">Female</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </TextField>
            )}
          />
          <Controller
            name="date_of_birth"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Date of Birth"
                type="date"
                fullWidth
                margin="normal"
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
          <Controller
            name="address"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Address"
                fullWidth
                margin="normal"
                multiline
                rows={2}
              />
            )}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {loading ? 'Adding...' : 'Add Customer'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default AddCustomerModal;

