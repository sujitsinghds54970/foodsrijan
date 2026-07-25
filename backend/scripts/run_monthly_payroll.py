from __future__ import annotations

from datetime import datetime

from app.database import SessionLocal
from app.models.hr import DirectorNotification
from app.models.payroll.models import PayrollRunStatus
from app.services.payroll_engine import generate_payroll_run


def run_monthly_payroll() -> None:
    """Run on 1st day each month for previous month payroll draft generation."""
    now = datetime.utcnow()
    if now.month == 1:
        target_month = 12
        target_year = now.year - 1
    else:
        target_month = now.month - 1
        target_year = now.year

    db = SessionLocal()
    try:
        from app.models import Branch

        branches = db.query(Branch).all()
        for branch in branches:
            run = generate_payroll_run(
                db=db,
                branch_id=branch.id,
                month=target_month,
                year=target_year,
                generated_by_user_id=None,
            )
            run.status = PayrollRunStatus.DRAFT

            db.add(
                DirectorNotification(
                    director_user_id=1,
                    branch_id=branch.id,
                    title="Monthly Payroll Draft Ready",
                    message=(
                        f"Payroll draft for {target_month:02d}/{target_year} generated. "
                        "Please review and approve."
                    ),
                )
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_monthly_payroll()
    print("Monthly payroll draft generation completed")
