"""Executive aggregate helpers for B2/B3 derived metrics."""

from app.services.aggregations.alerts import compute_critical_alerts
from app.services.aggregations.cash import compute_cash_conversion, compute_performance_summary
from app.services.aggregations.customers import compute_customer_activity
from app.services.aggregations.decisions import compute_decision_queue
from app.services.aggregations.portfolio import compute_portfolio_health, compute_strategy_okrs
from app.services.aggregations.revenue import compute_group_revenue, compute_revenue_trend

__all__ = [
    "compute_group_revenue",
    "compute_revenue_trend",
    "compute_customer_activity",
    "compute_critical_alerts",
    "compute_decision_queue",
    "compute_portfolio_health",
    "compute_strategy_okrs",
    "compute_cash_conversion",
    "compute_performance_summary",
]
