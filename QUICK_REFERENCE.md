# Quick Reference: Multi-Stage Loan Approval

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAN APPROVAL WORKFLOW                    │
└─────────────────────────────────────────────────────────────┘

   CREATE LOAN
       │
       ▼
   ┌─────────┐
   │ PENDING │ ◄─── Staff/Loan Collector creates loan
   └─────────┘
       │
       │ Staff approves (/loans/<id>/approve-staff)
       ▼
   ┌───────────────────────────┐
   │ PENDING_MANAGER_APPROVAL  │ ◄─── Awaiting manager review
   └───────────────────────────┘
       │
       │ Manager approves (/loans/<id>/approve-manager)
       ▼
   ┌──────────┐
   │INITIATED │ ◄─── Ready for disbursement
   └──────────┘
       │
       │ Admin approves & disburses (/loans/<id>/approve-admin)
       ▼
   ┌────────┐
   │ ACTIVE │ ◄─── Loan disbursed, payments can begin
   └────────┘
       │
       │ All payments collected
       ▼
   ┌───────────┐
   │ COMPLETED │
   └───────────┘

   Any stage can be REJECTED ───────────► [REJECTED]
```

## Database Migration

**IMPORTANT**: Run this to apply the changes:

```bash
cd /Users/kevinbrinsly/JaanNetworkProjects/JaanMicro
source .venv/bin/activate
flask db upgrade
```

Or manually apply the migration file:
- `migrations/versions/f1234567890a_add_multi_stage_loan_approval_workflow.py`

## Status Descriptions

| Status | Description | Who Can Approve | Next Action |
|--------|-------------|-----------------|-------------|
| `pending` | Newly created loan | Staff/Loan Collector | Staff approval |
| `pending_manager_approval` | Staff approved | Manager/Accountant | Manager approval |
| `initiated` | Manager approved | Admin | Final approval & disburse |
| `active` | Disbursed and active | - | Collect payments |
| `completed` | Fully paid | - | Archive |
| `rejected` | Rejected at any stage | - | Review/recreate |

## User Roles & Permissions

### Staff / Loan Collector
- ✓ Create loans
- ✓ First-stage approval (pending → pending_manager_approval)
- ✗ Cannot approve manager/admin stages

### Manager / Accountant
- ✓ Second-stage approval (pending_manager_approval → initiated)
- ✗ Cannot approve staff stage
- ✗ Cannot disburse loans

### Admin
- ✓ Final approval & disbursement (initiated → active)
- ✓ Quick approve (bypass workflow) - for emergency cases
- ✓ Full system access

## Key Routes

| Route | Method | Description | Access |
|-------|--------|-------------|--------|
| `/loans/add` | GET/POST | Create new loan | Staff+ |
| `/loans/<id>` | GET | View loan details | All |
| `/loans/<id>/approve-staff` | GET/POST | Staff approval | Staff, Loan Collector |
| `/loans/<id>/approve-manager` | GET/POST | Manager approval | Manager, Accountant |
| `/loans/<id>/approve-admin` | GET/POST | Admin approval | Admin |
| `/loans/<id>/approve` | GET/POST | Legacy quick approve | Admin (legacy) |

## Testing the Implementation

1. **Create a test loan**:
   - Login as staff
   - Navigate to Loans → Add Loan
   - Fill in details, keep status as "Pending"
   - Save

2. **Staff Approval**:
   - Login as staff
   - View the loan
   - Click "Staff Approval" button
   - Approve the loan
   - Status changes to "Pending Manager Approval"

3. **Manager Approval**:
   - Login as manager
   - View the loan
   - Click "Manager Approval" button
   - Approve the loan
   - Status changes to "Initiated"

4. **Admin Disbursement**:
   - Login as admin
   - View the loan
   - Click "Admin Approval & Disburse" button
   - Fill disbursement details
   - Approve
   - Status changes to "Active"
   - Loan is now ready for payments

## Visual Indicators

### Loan List View
- Status badges show color-coded current status
- Yellow: Pending
- Orange: Pending Manager Approval
- Cyan: Initiated
- Green: Active
- Red: Rejected

### Loan Detail View
- Progress indicator shows completed and pending stages
- ✓ Green checkmark: Completed stage
- ⏰ Yellow clock: Current/pending stage
- ⚪ Gray circle: Upcoming stage
- Displays approver names and dates for completed stages

## Approval Notes

Each approval stage supports notes:
- `staff_approval_notes`
- `manager_approval_notes`
- `admin_approval_notes`

These notes are displayed in the loan view page under the workflow status section.

## Activity Logging

All approval actions are automatically logged:
- `staff_approve_loan` / `staff_reject_loan`
- `manager_approve_loan` / `manager_reject_loan`
- `admin_approve_loan` / `admin_reject_loan`

View logs in the activity log table or reports section.

## Troubleshooting

### "Can't locate revision" error during migration
- Check that all migration files exist in `migrations/versions/`
- The new migration depends on: `eb7e3d3d31df` (previous migration)
- If issues persist, you may need to stamp the database or recreate migrations

### Approval button not showing
- Verify user role matches the required role for that stage
- Check loan status matches the expected status
- Ensure permissions are set correctly for the user

### Workflow not progressing
- Verify each approval stage is being completed
- Check the database for `staff_approved_by`, `manager_approved_by` fields
- Review activity logs for any errors

## API/Database Schema

### New Columns in `loans` table:

```sql
-- Staff approval
staff_approved_by INTEGER REFERENCES users(id)
staff_approval_date DATE
staff_approval_notes TEXT

-- Manager approval  
manager_approved_by INTEGER REFERENCES users(id)
manager_approval_date DATE
manager_approval_notes TEXT

-- Admin approval
admin_approved_by INTEGER REFERENCES users(id)
admin_approval_date DATE
admin_approval_notes TEXT

-- General
approval_date DATE  -- Legacy
rejection_reason TEXT
status VARCHAR(30)  -- Increased from VARCHAR(20)
```

## Backward Compatibility

The implementation maintains backward compatibility:
- Legacy `approve_loan` route still works for admins
- Old status values (`pending`, `active`, `completed`, etc.) still work
- Existing `approved_by` field is populated on final admin approval
- No breaking changes to existing functionality

---

**Last Updated**: January 30, 2026
**Version**: 1.0
**Author**: GitHub Copilot
