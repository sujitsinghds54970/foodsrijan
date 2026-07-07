"""
STAFF MANAGEMENT MODULE - PART 2
Attendance, Salary, Performance, Scheduling, and Reporting Functions

This file contains the implementation of remaining functions that are too large
to fit in a single file. Import and integrate with staff_management.py
"""

# These implementations should be added to the StaffManagementSystem class in staff_management.py

# ==================== ATTENDANCE FUNCTIONS IMPLEMENTATION ====================

def mark_attendance_impl(self, employee_id: str, check_in_time: datetime, 
                   check_out_time: Optional[datetime] = None, 
                   location: Optional[str] = None) -> str:
    """Mark attendance implementation"""
    try:
        # Verify staff exists
        staff = self.get_staff_details(employee_id)
        
        attendance_date = check_in_time.date()
        year = attendance_date.year
        month = attendance_date.month
        
        # Get attendance file
        attendance_path = self._get_excel_file_path('attendance', year=year, month=month)
        self._ensure_file_exists(attendance_path, 'attendance')
        
        # Generate attendance ID
        attendance_id = f"ATT-{self.branch_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate late minutes and overtime
        work_schedule = staff.get('work_schedule', {})
        standard_start = work_schedule.get('start_time', '09:00')
        standard_end = work_schedule.get('end_time', '18:00')
        
        late_minutes = 0
        overtime_minutes = 0
        
        # Calculate late coming
        if check_in_time.time() > datetime.strptime(standard_start, '%H:%M').time():
            late_minutes = int((check_in_time.time().hour * 60 + check_in_time.time().minute) - 
                             (datetime.strptime(standard_start, '%H:%M').hour * 60 + 
                              datetime.strptime(standard_start, '%H:%M').minute))
        
        # Calculate overtime if check_out provided
        if check_out_time:
            if check_out_time.time() > datetime.strptime(standard_end, '%H:%M').time():
                overtime_minutes = int((check_out_time.time().hour * 60 + check_out_time.time().minute) - 
                                     (datetime.strptime(standard_end, '%H:%M').hour * 60 + 
                                      datetime.strptime(standard_end, '%H:%M').minute))
        
        # Determine status
        status = AttendanceStatus.PRESENT.value
        if late_minutes > 120:  # More than 2 hours late
            status = AttendanceStatus.HALF_DAY.value
        
        # Create attendance record
        attendance_data = {
            'attendance_id': attendance_id,
            'employee_id': employee_id,
            'date': attendance_date,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'status': status,
            'location': location,
            'late_minutes': late_minutes,
            'overtime_minutes': overtime_minutes,
            'remarks': None
        }
        
        # Add to attendance sheet
        attendance_df = self._read_excel_safe(attendance_path, 'Daily_Attendance')
        new_row = pd.DataFrame([attendance_data])
        updated_df = pd.concat([attendance_df, new_row], ignore_index=True)
        self._write_excel_safe(attendance_path, updated_df, 'Daily_Attendance')
        
        # Log audit
        self._log_audit('MARK_ATTENDANCE', employee_id, attendance_data)
        
        logger.info(f"Marked attendance for {employee_id}: {attendance_id}")
        return attendance_id
        
    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        raise


def apply_leave_impl(self, employee_id: str, leave_type: str, 
               from_date: date, to_date: date, reason: str) -> str:
    """Apply for leave implementation"""
    try:
        # Verify staff exists
        staff = self.get_staff_details(employee_id)
        
        # Calculate days
        days_count = (to_date - from_date).days + 1
        
        # Check leave balance
        leave_balance = self.get_leave_balance(employee_id)
        if leave_type in leave_balance and leave_balance[leave_type] < days_count:
            raise InsufficientLeaveBalanceError(
                f"Insufficient {leave_type} balance. Available: {leave_balance[leave_type]}, Requested: {days_count}"
            )
        
        # Generate leave ID
        leave_id = f"LV-{self.branch_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create leave request
        leave_data = {
            'leave_id': leave_id,
            'employee_id': employee_id,
            'leave_type': leave_type,
            'from_date': from_date,
            'to_date': to_date,
            'days_count': days_count,
            'reason': reason,
            'status': 'Pending',
            'applied_date': datetime.now(),
            'approved_by': None,
            'approved_date': None
        }
        
        # Add to leave records
        year = from_date.year
        month = from_date.month
        attendance_path = self._get_excel_file_path('attendance', year=year, month=month)
        self._ensure_file_exists(attendance_path, 'attendance')
        
        leave_df = self._read_excel_safe(attendance_path, 'Leave_Records')
        new_row = pd.DataFrame([leave_data])
        updated_df = pd.concat([leave_df, new_row], ignore_index=True)
        self._write_excel_safe(attendance_path, updated_df, 'Leave_Records')
        
        # Log audit
        self._log_audit('APPLY_LEAVE', employee_id, leave_data)
        
        logger.info(f"Leave applied for {employee_id}: {leave_id}")
        return leave_id
        
    except Exception as e:
        logger.error(f"Error applying leave: {e}")
        raise


def get_leave_balance_impl(self, employee_id: str) -> Dict[str, float]:
    """Get leave balance implementation"""
    try:
        # Default annual leave allocation
        leave_allocation = {
            LeaveType.SICK.value: 12,
            LeaveType.CASUAL.value: 12,
            LeaveType.EARNED.value: 15,
            LeaveType.UNPAID.value: 999,  # Unlimited
            LeaveType.MATERNITY.value: 180,
            LeaveType.PATERNITY.value: 15,
            LeaveType.COMPENSATORY.value: 0
        }
        
        # Get all approved leaves for current year
        current_year = datetime.now().year
        total_used = {k: 0.0 for k in leave_allocation.keys()}
        
        for month in range(1, 13):
            try:
                attendance_path = self._get_excel_file_path('attendance', year=current_year, month=month)
                if not attendance_path.exists():
                    continue
                    
                leave_df = self._read_excel_safe(attendance_path, 'Leave_Records')
                if leave_df.empty:
                    continue
                
                # Filter approved leaves for this employee
                employee_leaves = leave_df[
                    (leave_df['employee_id'] == employee_id) & 
                    (leave_df['status'] == 'Approved')
                ]
                
                for _, leave in employee_leaves.iterrows():
                    leave_type = leave['leave_type']
                    if leave_type in total_used:
                        total_used[leave_type] += leave['days_count']
            except:
                continue
        
        # Calculate balance
        balance = {}
        for leave_type, allocated in leave_allocation.items():
            balance[leave_type] = allocated - total_used.get(leave_type, 0)
        
        return balance
        
    except Exception as e:
        logger.error(f"Error getting leave balance: {e}")
        return {}


# ==================== SALARY FUNCTIONS IMPLEMENTATION ====================

def create_salary_structure_impl(self, employee_id: str, components: Dict[str, float]) -> bool:
    """Create salary structure implementation"""
    try:
        # Verify staff exists
        staff = self.get_staff_details(employee_id)
        
        # Calculate gross and net salary
        basic = components.get('basic_salary', 0)
        hra = components.get('hra', basic * 0.4)  # 40% of basic
        da = components.get('da', basic * 0.1)  # 10% of basic
        medical = components.get('medical_allowance', 1250)
        conveyance = components.get('conveyance_allowance', 1600)
        special = components.get('special_allowance', 0)
        
        gross_salary = basic + hra + da + medical + conveyance + special
        
        # Calculate deductions
        pf = components.get('pf_contribution', basic * 0.12)  # 12% of basic
        esi = components.get('esi_contribution', gross_salary * 0.0075 if gross_salary <= 21000 else 0)
        pt = components.get('professional_tax', 200)
        tds = components.get('tds', 0)
        other_deductions = components.get('other_deductions', 0)
        
        total_deductions = pf + esi + pt + tds + other_deductions
        net_salary = gross_salary - total_deductions
        
        # Prepare salary structure
        salary_data = {
            'employee_id': employee_id,
            'basic_salary': basic,
            'hra': hra,
            'da': da,
            'medical_allowance': medical,
            'conveyance_allowance': conveyance,
            'special_allowance': special,
            'pf_contribution': pf,
            'esi_contribution': esi,
            'professional_tax': pt,
            'tds': tds,
            'other_deductions': other_deductions,
            'gross_salary': gross_salary,
            'net_salary': net_salary,
            'effective_from': components.get('effective_from', date.today())
        }
        
        # Save to salary file
        current_year = datetime.now().year
        salary_path = self._get_excel_file_path('salary', year=current_year)
        self._ensure_file_exists(salary_path, 'salary')
        
        salary_df = self._read_excel_safe(salary_path, 'Salary_Structure')
        
        # Remove old structure for this employee
        salary_df = salary_df[salary_df['employee_id'] != employee_id]
        
        # Add new structure
        new_row = pd.DataFrame([salary_data])
        updated_df = pd.concat([salary_df, new_row], ignore_index=True)
        self._write_excel_safe(salary_path, updated_df, 'Salary_Structure')
        
        # Log audit
        self._log_audit('CREATE_SALARY_STRUCTURE', employee_id, salary_data)
        
        logger.info(f"Created salary structure for {employee_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating salary structure: {e}")
        raise


def process_monthly_salary_impl(self, year: int, month: int, 
                          department_filter: Optional[str] = None) -> Dict[str, Any]:
    """Process monthly salary implementation"""
    try:
        # Get all active staff
        filters = {'is_active': True}
        if department_filter:
            filters['department'] = department_filter
        
        all_staff = self.get_all_staff(filters)
        
        if all_staff.empty:
            return {'processed': 0, 'total_amount': 0, 'details': []}
        
        salary_path = self._get_excel_file_path('salary', year=year)
        self._ensure_file_exists(salary_path, 'salary')
        
        salary_structure_df = self._read_excel_safe(salary_path, 'Salary_Structure')
        monthly_salary_df = self._read_excel_safe(salary_path, 'Monthly_Salary')
        
        processed_count = 0
        total_amount = 0
        details = []
        
        for _, staff in all_staff.iterrows():
            employee_id = staff['employee_id']
            
            # Check if already processed
            existing = monthly_salary_df[
                (monthly_salary_df['employee_id'] == employee_id) &
                (monthly_salary_df['month'] == month) &
                (monthly_salary_df['year'] == year)
            ]
            
            if not existing.empty:
                continue
            
            # Get salary structure
            salary_struct = salary_structure_df[salary_structure_df['employee_id'] == employee_id]
            
            if salary_struct.empty:
                logger.warning(f"No salary structure found for {employee_id}")
                continue
            
            salary_info = salary_struct.iloc[0]
            
            # Calculate attendance-based deductions
            attendance_summary = self.get_attendance_summary(
                employee_id, 
                (date(year, month, 1), date(year, month, 28))
            )
            
            # Adjust salary based on attendance
            working_days = attendance_summary.get('working_days', 26)
            present_days = attendance_summary.get('present_days', 0)
            
            if present_days < working_days:
                # Deduct for absent days
                per_day_salary = salary_info['gross_salary'] / working_days
                absent_deduction = (working_days - present_days) * per_day_salary
            else:
                absent_deduction = 0
            
            gross = salary_info['gross_salary']
            deductions = (salary_info['pf_contribution'] + 
                         salary_info['esi_contribution'] + 
                         salary_info['professional_tax'] + 
                         salary_info['tds'] + 
                         salary_info['other_deductions'] + 
                         absent_deduction)
            
            net = gross - deductions
            
            # Create monthly salary record
            monthly_data = {
                'employee_id': employee_id,
                'month': month,
                'year': year,
                'basic': salary_info['basic_salary'],
                'allowances': (salary_info['hra'] + salary_info['da'] + 
                             salary_info['medical_allowance'] + 
                             salary_info['conveyance_allowance'] + 
                             salary_info['special_allowance']),
                'gross': gross,
                'deductions': deductions,
                'net_salary': net,
                'payment_date': None,
                'payment_mode': None,
                'status': 'Processed'
            }
            
            # Add to monthly salary
            new_row = pd.DataFrame([monthly_data])
            monthly_salary_df = pd.concat([monthly_salary_df, new_row], ignore_index=True)
            
            processed_count += 1
            total_amount += net
            details.append({
                'employee_id': employee_id,
                'name': staff['full_name'],
                'net_salary': net
            })
        
        # Save updated monthly salary
        self._write_excel_safe(salary_path, monthly_salary_df, 'Monthly_Salary')
        
        # Log audit
        self._log_audit('PROCESS_MONTHLY_SALARY', 'SYSTEM', {
            'year': year,
            'month': month,
            'processed': processed_count,
            'total_amount': total_amount
        })
        
        logger.info(f"Processed salary for {processed_count} employees")
        
        return {
            'processed': processed_count,
            'total_amount': total_amount,
            'details': details
        }
        
    except Exception as e:
        logger.error(f"Error processing monthly salary: {e}")
        raise


def calculate_pf_contribution_impl(self, basic_salary: float) -> Dict[str, float]:
    """Calculate PF contribution implementation"""
    # PF calculation as per Indian rules
    pf_ceiling = 15000  # Maximum basic for PF calculation
    
    pf_basic = min(basic_salary, pf_ceiling)
    employee_contribution = pf_basic * 0.12  # 12%
    employer_contribution = pf_basic * 0.12  # 12%
    
    # Employer contribution breakdown
    epf = pf_basic * 0.0367  # 3.67% to EPF
    eps = pf_basic * 0.0833  # 8.33% to EPS
    edli = pf_basic * 0.005   # 0.5% to EDLI
    admin_charges = pf_basic * 0.0065  # 0.65% admin charges
    
    return {
        'employee_contribution': round(employee_contribution, 2),
        'employer_contribution': round(employer_contribution, 2),
        'epf': round(epf, 2),
        'eps': round(eps, 2),
        'edli': round(edli, 2),
        'admin_charges': round(admin_charges, 2),
        'total_pf': round(employee_contribution + employer_contribution, 2)
    }


# ==================== EXAMPLE USAGE AND TESTING ====================

def example_usage_complete():
    """Complete example usage of the staff management system"""
    
    # Initialize system
    branch_config = BranchConfig(
        branch_id="BR001",
        branch_name="Main Branch",
        branch_code="MAIN",
        base_data_path="./data/staff"
    )
    
    sms = StaffManagementSystem(branch_config)
    
    # Example 1: Add new staff member
    staff_data = {
        'full_name': 'Dr. Rajesh Kumar',
        'date_of_birth': date(1985, 5, 15),
        'gender': 'Male',
        'blood_group': 'O+',
        'phone': '9876543210',
        'email': 'rajesh.kumar@example.com',
        'emergency_contact': '9876543211',
        'emergency_contact_name': 'Mrs. Kumar',
        'emergency_contact_relation': 'Spouse',
        'address': '123 Main Street, City',
        'pan_number': 'ABCDE1234F',
        'aadhar_number': '123456789012',
        'bank_account_number': '1234567890',
        'bank_name': 'State Bank',
        'bank_ifsc': 'SBIN0001234',
        'designation': 'Senior Pathologist',
        'department': 'Pathology',
        'reporting_manager': None,
        'joining_date': date(2020, 1, 1),
        'employment_type': 'Full-Time',
        'work_schedule': {
            'start_time': '09:00',
            'end_time': '18:00',
            'working_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        }
    }
    
    employee_id = sms.add_staff_member(staff_data)
    print(f"Added staff: {employee_id}")
    
    # Example 2: Create salary structure
    salary_components = {
        'basic_salary': 50000,
        'hra': 20000,
        'da': 5000,
        'medical_allowance': 1250,
        'conveyance_allowance': 1600,
        'special_allowance': 10000,
        'effective_from': date.today()
    }
    
    sms.create_salary_structure(employee_id, salary_components)
    print("Salary structure created")
    
    # Example 3: Mark attendance
    attendance_id = sms.mark_attendance(
        employee_id,
        datetime.now().replace(hour=9, minute=15),
        datetime.now().replace(hour=18, minute=30),
        location="Main Branch"
    )
    print(f"Attendance marked: {attendance_id}")
    
    # Example 4: Apply leave
    leave_id = sms.apply_leave(
        employee_id,
        LeaveType.CASUAL.value,
        date.today() + timedelta(days=7),
        date.today() + timedelta(days=9),
        "Personal work"
    )
    print(f"Leave applied: {leave_id}")
    
    # Example 5: Get staff details
    details = sms.get_staff_details(employee_id)
    print(f"Staff details: {details['full_name']}, {details['designation']}")
    
    # Example 6: Search staff
    results = sms.search_staff("Rajesh", "name")
    print(f"Search results: {len(results)} found")
    
    # Example 7: Get upcoming birthdays
    birthdays = sms.get_upcoming_birthdays(30)
    print(f"Upcoming birthdays: {len(birthdays)}")
    
    # Example 8: Process monthly salary
    salary_summary = sms.process_monthly_salary(2026, 3)
    print(f"Processed salary for {salary_summary['processed']} employees")
    print(f"Total amount: ₹{salary_summary['total_amount']:,.2f}")


if __name__ == "__main__":
    print("Staff Management Module - Part 2")
    print("This file contains implementation functions to be integrated with staff_management.py")
