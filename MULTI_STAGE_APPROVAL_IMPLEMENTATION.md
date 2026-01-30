# Multi-Stage Loan Approval Workflow Implementation

## Overview
This document describes the multi-stage loan approval workflow that has been implemented for the JaanMicro application.

## Approval Workflow Stages

### Stage 1: Staff Approval (pending → pending_manager_approval)
- **Who**: Staff members or Loan Collectors
- **Route**: `/loans/<id>/approve-staff`
- **Actions**: 
  - Review loan application
  - Approve or Reject
  - Add approval notes
- **Next Status**: 
  - If approved: `pending_manager_approval`
  - If rejected: `rejected`

### Stage 2: Manager Approval (pending_manager_approval → initiated)
- **Who**: Managers or Accountants
- **Route**: `/loans/<id>/approve-manager`
- **Actions**:
  - Review loan and staff approval
  - Approve or Reject
  - Add approval notes
- **Next Status**:
  - If approved: `initiated`
  - If rejected: `rejected`

### Stage 3: Admin Approval & Disbursement (initiated → active)
- **Who**: Admin only
- **Route**: `/loans/<id>/approve-admin`
- **Actions**:
  - Final review of loan
  - Set disbursement details (amount, date, method, reference)
  - Set first installment date
  - Calculate maturity date
  - Approve or Reject
- **Next Status**:
  - If approved: `active` (loan is disbursed and payments can begin)
  - If rejected: `rejected`

## Loan Status Flow

```
pending
   ↓ (Staff approves)
pending_manager_approval
   ↓ (Manager approves)
initiated
   ↓ (Admin approves & disburses)
active
   ↓ (Payments complete)
completed
```

At any stage, the loan can be rejected and will move to `rejected` status.

## Database Changes

### New Fields Added to `loans` Table:
1. **Staff Approval**:
   - `staff_approved_by` (Integer, Foreign Key to users.id)
   - `staff_approval_date` (Date)
   - `staff_approval_notes` (Text)

2. **Manager Approval**:
   - `manager_approved_by` (Integer, Foreign Key to users.id)
   - `manager_approval_date` (Date)
   - `manager_approval_notes` (Text)

3. **Admin Approval**:
   - `admin_approved_by` (Integer, Foreign Key to users.id)
   - `admin_approval_date` (Date)
   - `admin_approval_notes` (Text)

4. **Other**:
   - `approval_date` (Date) - Legacy field for backward compatibility
   - `rejection_reason` (Text)
   - `status` column increased from VARCHAR(20) to VARCHAR(30)

### New Statuses:
- `pending` - Initial status when loan is created
- `pending_staff_approval` - (Not currently used, reserved for future)
- `pending_manager_approval` - After staff approval
- `initiated` - After manager approval, ready for disbursement
- `active` - After admin approval and disbursement
- `completed` - Loan fully paid
- `rejected` - Rejected at any stage
- `defaulted` - Loan defaulted

## Files Modified

### 1. Models (`app/models.py`)
- Added multi-stage approval fields to `Loan` model
- Added relationships: `staff_approver`, `manager_approver`, `admin_approver`

### 2. Forms (`app/loans/forms.py`)
- `StaffApprovalForm` - For staff approval
- `ManagerApprovalForm` - For manager approval
- `AdminApprovalForm` - For admin approval and disbursement
- `InitiateLoanForm` - Reserved for future use

### 3. Routes (`app/loans/routes.py`)
- `approve_loan_staff()` - Staff approval endpoint
- `approve_loan_manager()` - Manager approval endpoint
- `approve_loan_admin()` - Admin approval endpoint

### 4. Templates
- `app/templates/loans/approve_staff.html` - Staff approval form
- `app/templates/loans/approve_manager.html` - Manager approval form
- `app/templates/loans/approve_admin.html` - Admin approval form
- `app/templates/loans/view.html` - Updated with approval workflow progress indicator
- `app/templates/loans/list.html` - Updated to show new status labels
- `app/templates/base.html` - Added CSS for new status badges

### 5. Migrations
- `migrations/versions/f1234567890a_add_multi_stage_loan_approval_workflow.py`

## Role-Based Access Control

| Role | Can Staff Approve | Can Manager Approve | Can Admin Approve |
|------|------------------|---------------------|-------------------|
| Staff | ✓ | ✗ | ✗ |
| Loan Collector | ✓ | ✗ | ✗ |
| Accountant | ✗ | ✓ | ✗ |
| Manager | ✗ | ✓ | ✗ |
| Admin | Quick Approve* | ✗ | ✓ |

*Admin has a "Quick Approve" option that bypasses the multi-stage workflow for urgent cases (legacy single-stage approval).

## Features

### Visual Workflow Indicator
- Each approval template shows a visual progress indicator
- Shows which stages are completed, pending, or upcoming
- Displays approver names and dates for completed stages

### Approval Notes
- Each stage can have approval notes
- Notes are displayed in the loan view
- Helps track decision-making process

### Rejection Handling
- Loans can be rejected at any stage
- Rejection reason is required
- Rejected loans cannot proceed to next stages

### Backward Compatibility
- Legacy `approved_by`, `approval_date`, and `approval_notes` fields maintained
- Admin approval populates both new and legacy fields
- Existing single-stage approval route (`/loans/<id>/approve`) still works for admins

## Usage Instructions

### To Apply the Database Migration:
```bash
cd /Users/kevinbrinsly/JaanNetworkProjects/JaanMicro
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
flask db upgrade
```

### Typical Workflow:

1. **Staff/Loan Collector creates loan** → Status: `pending`

2. **Staff/Loan Collector approves** → Status: `pending_manager_approval`
   - Go to loan details
   - Click "Staff Approval" button
   - Fill in approval form
   - Submit

3. **Manager/Accountant approves** → Status: `initiated`
   - Go to loan details
   - Click "Manager Approval" button
   - Fill in approval form
   - Submit

4. **Admin disburses loan** → Status: `active`
   - Go to loan details
   - Click "Admin Approval & Disburse" button
   - Fill in disbursement details
   - Submit

5. **Payments are collected** → Loan becomes `completed` when fully paid

## Activity Logging

Each approval action is logged in the `ActivityLog` table with:
- Action type: `staff_approve_loan`, `manager_approve_loan`, `admin_approve_loan`
- User who performed the action
- Timestamp
- IP address
- Description

## Benefits

1. **Better Control**: Multi-layer approval ensures proper scrutiny
2. **Audit Trail**: Complete history of who approved at each stage
3. **Risk Management**: Reduces risk of fraudulent or poorly assessed loans
4. **Accountability**: Clear responsibility at each stage
5. **Flexibility**: Admin quick approve option for urgent cases

## Future Enhancements

Potential additions:
- Email/SMS notifications at each approval stage
- Automatic rejection after timeout
- Approval limits based on loan amount
- Delegation of approval authority
- Batch approval for multiple loans
- Approval comments/discussion thread
