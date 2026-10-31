from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable

from app.models import DailyAnalyticsSnapshot
from app.models.daily_entry_module import DailyEntryModule
from app.services.aggregations.querying import branch_scoped_query
from app.services.executive_metrics import MetricResult


_FIELD_NAMES = ("amount", "total_amount", "net_amount", "revenue", "total_revenue", "gross_amount")


def _safe_number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match is None:
            return 0.0
        return float(match.group(0))
    return 0.0

def _sum_numeric_values(rows: Iterable[Any], field_names: tuple[str, ...] = _FIELD_NAMES) -> float:
    total = 0.0
    for row in rows:
        for field_name in field_names:
            value = getattr(row, field_name, None)
            if value is None and isinstance(row, dict):
                value = row.get(field_name)
            if value is not None:
                total += _safe_number(value)
                break
    return total


@dataclass(frozen=True)
class RevenueSource:
    name: str
    rows: list[Any]
    reconciled: bool
    date_field: str
    value_fields: tuple[str, ...]


def _select_revenue_source(db: Any, scope: Any) -> RevenueSource:
    snapshot_rows = branch_scoped_query(db, DailyAnalyticsSnapshot, scope).order_by(DailyAnalyticsSnapshot.date.asc()).all()
    if snapshot_rows:
        return RevenueSource("daily_analytics_snapshots", snapshot_rows, True, "date", ("total_revenue",))
    entry_rows = branch_scoped_query(db, DailyEntryModule, scope).order_by(DailyEntryModule.auto_entry_datetime.asc()).all()
    if entry_rows:
        return RevenueSource("daily_entry_modules", entry_rows, False, "auto_entry_datetime", ("total_amount", "fee_amount"))
    return RevenueSource("none", [], False, "date", ("total_revenue",))


def _row_date(row: Any, field_name: str) -> date | None:
    value = getattr(row, field_name, None)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _period_days(period: str | None, max_date: date) -> int:
    if not period:
        return 30
    normalized = period.strip().lower()
    match = re.fullmatch(r"(\d+)\s*d(?:ays?)?", normalized)
    if match:
        return max(1, int(match.group(1)))
    if normalized in {"mtd", "month"}:
        return (max_date - max_date.replace(day=1)).days + 1
    if normalized in {"qtd", "quarter"}:
        quarter_month = ((max_date.month - 1) // 3) * 3 + 1
        return (max_date - max_date.replace(month=quarter_month, day=1)).days + 1
    if normalized in {"ytd", "year"}:
        return (max_date - max_date.replace(month=1, day=1)).days + 1
    return 30


def compute_group_revenue(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    revenue_source = _select_revenue_source(db, scope)
    total = _sum_numeric_values(revenue_source.rows, revenue_source.value_fields)
    status = "unavailable" if not revenue_source.rows else ("complete" if revenue_source.reconciled else "partial")
    return MetricResult(
        value=round(total, 2) if revenue_source.rows else None,
        display_value=f"₹{total:,.2f}" if revenue_source.rows else "—",
        delta=None,
        trend="unknown" if not revenue_source.rows else "flat",
        source=revenue_source.name,
        source_status=status,
        as_of=datetime.now(timezone.utc),
        confidence_level="high" if revenue_source.reconciled else "medium" if revenue_source.rows else "none",
        reconciled=revenue_source.reconciled,
        missing_sources=[] if revenue_source.rows else ["daily_analytics_snapshots", "daily_entry_modules"],
        unavailable_reason=None if revenue_source.rows else "No daily analytics snapshots or daily entries are available for this scope.",
        unit="currency",
        metric_name="group_revenue",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
    )

def compute_revenue_trend(db: Any, scope: Any, period: str | None = None) -> MetricResult:
    started = time.perf_counter()
    revenue_source = _select_revenue_source(db, scope)
    if not revenue_source.rows:
        return MetricResult(
            value=None,
            display_value="—",
            delta=None,
            trend="unknown",
            source=revenue_source.name,
            source_status="unavailable",
            as_of=datetime.now(timezone.utc),
            confidence_level="none",
            reconciled=revenue_source.reconciled,
            missing_sources=["daily_analytics_snapshots", "daily_entry_modules"],
            unavailable_reason="No daily analytics snapshots or daily entries are available for this scope.",
            unit="percent",
            metric_name="revenue_trend",
            computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
            details={"current_period_days": 0, "previous_period_days": 0, "same_length_previous_period": True},
        )
    dated_rows = [(row, _row_date(row, revenue_source.date_field)) for row in revenue_source.rows]
    usable_dates = [row_date for _, row_date in dated_rows if row_date is not None]
    max_date = max(usable_dates) if usable_dates else datetime.now(timezone.utc).date()
    days = _period_days(period, max_date)
    current_start = max_date - timedelta(days=days - 1)
    previous_start = current_start - timedelta(days=days)
    previous_end = current_start - timedelta(days=1)
    current_rows = [row for row, row_date in dated_rows if row_date is not None and current_start <= row_date <= max_date]
    previous_rows = [row for row, row_date in dated_rows if row_date is not None and previous_start <= row_date <= previous_end]
    current_total = _sum_numeric_values(current_rows, revenue_source.value_fields)
    previous_total = _sum_numeric_values(previous_rows, revenue_source.value_fields)
    delta = round(((current_total - previous_total) / previous_total * 100), 2) if previous_total else None
    trend = "unknown" if delta is None else "up" if delta > 0 else "down" if delta < 0 else "flat"
    sparkline_points = [
        {"date": row_date.isoformat(), "value": round(_sum_numeric_values([row], revenue_source.value_fields), 2)}
        for row, row_date in dated_rows
        if row_date is not None and current_start <= row_date <= max_date
    ]
    return MetricResult(
        value=delta,
        display_value=f"{delta:+.1f}%" if delta is not None else "—",
        delta=delta,
        trend=trend,
        source=revenue_source.name,
        source_status="complete" if previous_rows else "partial",
        as_of=datetime.now(timezone.utc),
        sparkline_points=sparkline_points,
        confidence_level="medium",
        reconciled=revenue_source.reconciled,
        unit="percent",
        metric_name="revenue_trend",
        computation_time_ms=max(0, int((time.perf_counter() - started) * 1000)),
        details={
            "current_period": {"start": current_start.isoformat(), "end": max_date.isoformat(), "days": days, "revenue": round(current_total, 2)},
            "previous_period": {"start": previous_start.isoformat(), "end": previous_end.isoformat(), "days": days, "revenue": round(previous_total, 2)},
            "same_length_previous_period": True,
        },
    )

__all__ = ["compute_group_revenue", "compute_revenue_trend"]
