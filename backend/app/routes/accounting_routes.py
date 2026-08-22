"""
Accounting Routes for VaidyaVihar Diagnostic ERP

Expense tracking and accounting endpoints:
- Expense management
- Income tracking
- Financial orders
- Budget management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.accounting import (
    ExpenseEntry, IncomeEntry, CategoryBudget, FinancialSummary, 
    ExpenseCategory, PaymentStatus
)

router = APIRouter()


# Pydantic Schemas
class ExpenseCreate(BaseModel):
    expense_date: Optional[datetime] = None
    category: str
    subcategory: Optional[str] = None
    description: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    amount: float
    tax_amount: float = 0
    payment_mode: str = "cash"
    payment_status: str = "pending"
    branch_id: Optional[int] = None
    staff_id: Optional[int] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class ExpenseUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None


class IncomeCreate(BaseModel):
    income_date: Optional[datetime] = None
    category: str
    subcategory: Optional[str] = None
    description: str
    patient_id: Optional[int] = None
    invoice_id: Optional[int] = None
    amount: float
    tax_amount: float = 0
    payment_mode: str = "cash"
    branch_id: Optional[int] = None
    notes: Optional[str] = None


class BudgetCreate(BaseModel):
    category: str
    budget_amount: float
    start_date: datetime
    end_date: datetime
    branch_id: Optional[int] = None
    alert_threshold_percent: int = 80


# Helper functions
def get_date_range(period: str):
    """Get date range based on period"""
    today = datetime.now().date()
    
    if period == "today":
        return datetime.combine(today, datetime.min.time()), datetime.combine(today, datetime.max.time())
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return datetime.combine(yesterday, datetime.min.time()), datetime.combine(yesterday, datetime.max.time())
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
    elif period == "month":
        start = today.replace(day=1)
        return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
    elif period == "quarter":
        quarter = (today.month - 1) // 3
        start_month = quarter * 3 + 1
        start = today.replace(month=start_month, day=1)
        return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
    elif period == "year":
        start = today.replace(month=1, day=1)
        return datetime.combine(start, datetime.min.time()), datetime.combine(today, datetime.max.time())
    else:
        return None, None


# Expense Endpoints
@router.post("/expenses")
async def create_expense(expense_data: ExpenseCreate, db: Session = Depends(get_db)):
    """Create a new expense"""
    total_amount = expense_data.amount + expense_data.tax_amount
    
    expense = ExpenseEntry(
        expense_date=expense_data.expense_date or datetime.utcnow(),
        category=ExpenseCategory(expense_data.category),
        subcategory=expense_data.subcategory,
        description=expense_data.description,
        vendor_name=expense_data.vendor_name,
        invoice_number=expense_data.invoice_number,
        amount=expense_data.amount,
        tax_amount=expense_data.tax_amount,
        total_amount=total_amount,
        payment_mode=expense_data.payment_mode,
        payment_status=PaymentStatus(expense_data.payment_status) if expense_data.payment_status else PaymentStatus.PENDING,
        branch_id=expense_data.branch_id,
        staff_id=expense_data.staff_id,
        notes=expense_data.notes,
        due_date=expense_data.due_date
    )
    
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    return {
        "success": True,
        "expense": {
            "id": expense.id,
            "expense_date": expense.expense_date.isoformat(),
            "category": expense.category.value if expense.category else None,
            "description": expense.description,
            "amount": expense.amount,
            "total_amount": expense.total_amount,
            "status": expense.status,
            "created_at": expense.created_at.isoformat()
        }
    }


@router.get("/expenses")
async def list_expenses(
    category: Optional[str] = None,
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    period: str = "month",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List expenses with filters"""
    query = db.query(ExpenseEntry)
    
    if category:
        query = query.filter(ExpenseEntry.category == ExpenseCategory(category))
    if status:
        query = query.filter(ExpenseEntry.status == status)
    if branch_id:
        query = query.filter(ExpenseEntry.branch_id == branch_id)
    
    # Date filter
    if start_date and end_date:
        query = query.filter(ExpenseEntry.expense_date.between(start_date, end_date))
    else:
        start, end = get_date_range(period)
        if start and end:
            query = query.filter(ExpenseEntry.expense_date.between(start, end))
    
    expenses = query.order_by(ExpenseEntry.expense_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "expenses": [
            {
                "id": exp.id,
                "expense_date": exp.expense_date.isoformat(),
                "category": exp.category.value if exp.category else None,
                "description": exp.description,
                "vendor_name": exp.vendor_name,
                "amount": exp.amount,
                "total_amount": exp.total_amount,
                "status": exp.status,
                "payment_status": exp.payment_status.value if exp.payment_status else None,
                "created_at": exp.created_at.isoformat()
            }
            for exp in expenses
        ]
    }


@router.get("/expenses/{expense_id}")
async def get_expense(expense_id: int, db: Session = Depends(get_db)):
    """Get expense details"""
    expense = db.query(ExpenseEntry).filter(ExpenseEntry.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {
        "success": True,
        "expense": {
            "id": expense.id,
            "expense_date": expense.expense_date.isoformat(),
            "category": expense.category.value if expense.category else None,
            "subcategory": expense.subcategory,
            "description": expense.description,
            "vendor_name": expense.vendor_name,
            "invoice_number": expense.invoice_number,
            "amount": expense.amount,
            "tax_amount": expense.tax_amount,
            "total_amount": expense.total_amount,
            "payment_mode": expense.payment_mode,
            "status": expense.status,
            "payment_status": expense.payment_status.value if expense.payment_status else None,
            "notes": expense.notes,
            "created_at": expense.created_at.isoformat()
        }
    }


@router.put("/expenses/{expense_id}")
async def update_expense(expense_id: int, expense_data: ExpenseUpdate, db: Session = Depends(get_db)):
    """Update expense"""
    expense = db.query(ExpenseEntry).filter(ExpenseEntry.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense_data.status:
        expense.status = expense_data.status
    if expense_data.payment_status:
        expense.payment_status = PaymentStatus(expense_data.payment_status)
    if expense_data.notes is not None:
        expense.notes = expense_data.notes
    
    # If marked as paid, update paid_date
    if expense_data.payment_status == "paid" and not expense.paid_date:
        expense.paid_date = datetime.utcnow()
    
    db.commit()
    db.refresh(expense)
    
    return {
        "success": True,
        "expense": {
            "id": expense.id,
            "status": expense.status,
            "payment_status": expense.payment_status.value if expense.payment_status else None
        }
    }


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete expense"""
    expense = db.query(ExpenseEntry).filter(ExpenseEntry.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    
    return {"success": True, "message": "Expense deleted"}


# Income Endpoints
@router.post("/income")
async def create_income(income_data: IncomeCreate, db: Session = Depends(get_db)):
    """Create a new income entry"""
    total_amount = income_data.amount + income_data.tax_amount
    
    income = IncomeEntry(
        income_date=income_data.income_date or datetime.utcnow(),
        category=income_data.category,
        subcategory=income_data.subcategory,
        description=income_data.description,
        patient_id=income_data.patient_id,
        invoice_id=income_data.invoice_id,
        amount=income_data.amount,
        tax_amount=income_data.tax_amount,
        total_amount=total_amount,
        payment_mode=income_data.payment_mode,
        branch_id=income_data.branch_id,
        notes=income_data.notes
    )
    
    db.add(income)
    db.commit()
    db.refresh(income)
    
    return {
        "success": True,
        "income": {
            "id": income.id,
            "income_date": income.income_date.isoformat(),
            "category": income.category,
            "description": income.description,
            "amount": income.amount,
            "total_amount": income.total_amount,
            "created_at": income.created_at.isoformat()
        }
    }


@router.get("/income")
async def list_income(
    category: Optional[str] = None,
    branch_id: Optional[int] = None,
    period: str = "month",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List income entries"""
    query = db.query(IncomeEntry)
    
    if category:
        query = query.filter(IncomeEntry.category == category)
    if branch_id:
        query = query.filter(IncomeEntry.branch_id == branch_id)
    
    start, end = get_date_range(period)
    if start and end:
        query = query.filter(IncomeEntry.income_date.between(start, end))
    
    income_entries = query.order_by(IncomeEntry.income_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "income": [
            {
                "id": inc.id,
                "income_date": inc.income_date.isoformat(),
                "category": inc.category,
                "description": inc.description,
                "amount": inc.amount,
                "total_amount": inc.total_amount,
                "created_at": inc.created_at.isoformat()
            }
            for inc in income_entries
        ]
    }


# Financial Summary Endpoints
@router.get("/summary")
async def get_financial_summary(
    period: str = "month",
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get financial summary for a period"""
    start, end = get_date_range(period)
    
    if not start or not end:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Calculate income
    income_query = db.query(IncomeEntry).filter(
        IncomeEntry.income_date.between(start, end)
    )
    if branch_id:
        income_query = income_query.filter(IncomeEntry.branch_id == branch_id)
    
    income_entries = income_query.all()
    total_income = sum(inc.total_amount for inc in income_entries)
    
    # Calculate expenses
    expense_query = db.query(ExpenseEntry).filter(
        ExpenseEntry.expense_date.between(start, end)
    )
    if branch_id:
        expense_query = expense_query.filter(ExpenseEntry.branch_id == branch_id)
    
    expense_entries = expense_query.all()
    total_expenses = sum(exp.total_amount for exp in expense_entries)
    
    # Calculate net profit
    net_profit = total_income - total_expenses
    
    # Income by category
    income_by_category = {}
    for inc in income_entries:
        cat = inc.category
        income_by_category[cat] = income_by_category.get(cat, 0) + inc.total_amount
    
    # Expenses by category
    expenses_by_category = {}
    for exp in expense_entries:
        cat = exp.category.value if exp.category else "other"
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + exp.total_amount
    
    return {
        "success": True,
        "summary": {
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_income * 100) if total_income > 0 else 0,
            "income_by_category": income_by_category,
            "expenses_by_category": expenses_by_category,
            "income_count": len(income_entries),
            "expense_count": len(expense_entries)
        }
    }


@router.get("/category-breakdown")
async def get_category_breakdown(
    period: str = "month",
    db: Session = Depends(get_db)
):
    """Get expense breakdown by category"""
    start, end = get_date_range(period)
    
    if not start or not end:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    expenses = db.query(ExpenseEntry).filter(
        ExpenseEntry.expense_date.between(start, end)
    ).all()
    
    breakdown = {}
    for exp in expenses:
        cat = exp.category.value if exp.category else "other"
        if cat not in breakdown:
            breakdown[cat] = {"total": 0, "count": 0, "items": []}
        breakdown[cat]["total"] += exp.total_amount
        breakdown[cat]["count"] += 1
        breakdown[cat]["items"].append({
            "id": exp.id,
            "description": exp.description,
            "amount": exp.total_amount,
            "date": exp.expense_date.isoformat()
        })
    
    return {
        "success": True,
        "breakdown": breakdown
    }


# Budget Endpoints
@router.post("/budgets")
async def create_budget(budget_data: BudgetCreate, db: Session = Depends(get_db)):
    """Create a budget"""
    budget = CategoryBudget(
        category=ExpenseCategory(budget_data.category),
        budget_amount=budget_data.budget_amount,
        start_date=budget_data.start_date,
        end_date=budget_data.end_date,
        branch_id=budget_data.branch_id,
        alert_threshold_percent=budget_data.alert_threshold_percent
    )
    
    db.add(budget)
    db.commit()
    db.refresh(budget)
    
    return {
        "success": True,
        "budget": {
            "id": budget.id,
            "category": budget.category.value if budget.category else None,
            "budget_amount": budget.budget_amount,
            "start_date": budget.start_date.isoformat(),
            "end_date": budget.end_date.isoformat()
        }
    }


@router.get("/budgets")
async def list_budgets(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List budgets"""
    query = db.query(CategoryBudget).filter(CategoryBudget.is_active == True)
    
    if branch_id:
        query = query.filter(CategoryBudget.branch_id == branch_id)
    
    budgets = query.all()
    
    # Calculate spent amounts
    result = []
    for budget in budgets:
        expenses = db.query(ExpenseEntry).filter(
            ExpenseEntry.category == budget.category,
            ExpenseEntry.expense_date.between(budget.start_date, budget.end_date)
        ).all()
        
        spent = sum(exp.total_amount for exp in expenses)
        percent_used = (spent / budget.budget_amount * 100) if budget.budget_amount > 0 else 0
        
        result.append({
            "id": budget.id,
            "category": budget.category.value if budget.category else None,
            "budget_amount": budget.budget_amount,
            "spent_amount": spent,
            "remaining": budget.budget_amount - spent,
            "percent_used": percent_used,
            "alert_threshold": budget.alert_threshold_percent,
            "is_over_budget": percent_used > budget.alert_threshold_percent,
            "start_date": budget.start_date.isoformat(),
            "end_date": budget.end_date.isoformat()
        })
    
    return {"success": True, "budgets": result}

