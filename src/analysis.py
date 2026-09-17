"""Reusable KPI, EDA, and business-question calculations for the dashboard."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"₹{value:,.0f}"


def percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{value:.1%}"


def _profit_margin(frame: pd.DataFrame) -> float:
    sales = frame["sales"].sum()
    return frame["estimated_profit"].sum() / sales if sales else np.nan


def known_records(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Remove unmatched placeholder values before ranking named business entities."""
    values = frame[column].astype("string")
    is_placeholder = values.str.lower().isin(["unknown", "unknown hotel", "<na>"]) | values.str.lower().str.startswith("unknown ")
    return frame.loc[frame[column].notna() & ~is_placeholder].copy()


def order_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Create one commercial record per booking for order-level KPI calculations."""
    return (
        frame.groupby("order_id", as_index=False, dropna=False)
        .agg(
            sales=("sales", "sum"),
            estimated_profit=("estimated_profit", "sum"),
            transaction_date=("transaction_date", "min"),
            customer=("Guest_Name", "first"),
            region=("region", "first"),
            product=("product", "first"),
            category=("category", "first"),
        )
    )


def kpis(frame: pd.DataFrame) -> dict[str, float | int | str]:
    orders = order_summary(frame)
    highest = orders.nlargest(1, "sales")
    return {
        "total_sales": float(frame["sales"].sum()),
        "estimated_profit": float(frame["estimated_profit"].sum()),
        "orders": int(orders["order_id"].nunique()),
        "average_order_value": float(orders["sales"].mean()) if not orders.empty else np.nan,
        "profit_margin": _profit_margin(frame),
        "highest_sales_order": int(highest.iloc[0]["order_id"]) if not highest.empty else 0,
        "highest_sales_order_value": float(highest.iloc[0]["sales"]) if not highest.empty else np.nan,
    }


def performance_by(frame: pd.DataFrame, dimension: str, top_n: int | None = None) -> pd.DataFrame:
    """Aggregate sales, estimated profit, orders, AOV, and margin by a dimension."""
    grouped = (
        frame.groupby(dimension, as_index=False, dropna=False)
        .agg(
            sales=("sales", "sum"),
            estimated_profit=("estimated_profit", "sum"),
            orders=("order_id", "nunique"),
            stays=("transaction_id", "nunique"),
            room_nights=("room_nights", "sum"),
        )
        .sort_values("sales", ascending=False)
    )
    grouped["average_order_value"] = grouped["sales"] / grouped["orders"].replace(0, np.nan)
    grouped["profit_margin"] = grouped["estimated_profit"] / grouped["sales"].replace(0, np.nan)
    return grouped.head(top_n) if top_n else grouped


def monthly_sales(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.dropna(subset=["month_start"])
        .groupby("month_start", as_index=False)
        .agg(sales=("sales", "sum"), estimated_profit=("estimated_profit", "sum"), orders=("order_id", "nunique"))
        .sort_values("month_start")
    )


def yearly_sales_growth(frame: pd.DataFrame) -> pd.DataFrame:
    yearly = (
        frame.dropna(subset=["year"])
        .groupby("year", as_index=False)
        .agg(sales=("sales", "sum"), estimated_profit=("estimated_profit", "sum"), orders=("order_id", "nunique"))
        .sort_values("year")
    )
    yearly["sales_growth"] = yearly["sales"].pct_change()
    return yearly


def top_customers(frame: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    frame = known_records(frame, "Guest_Name")
    return (
        frame.groupby(["Guest_ID", "Guest_Name", "customer_segment"], as_index=False, dropna=False)
        .agg(sales=("sales", "sum"), estimated_profit=("estimated_profit", "sum"), orders=("order_id", "nunique"))
        .sort_values("sales", ascending=False)
        .head(top_n)
    )


def discount_profit_analysis(frame: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    work = frame.dropna(subset=["discount_pct", "estimated_profit", "sales"]).copy()
    bins = [-0.01, 0, 5, 10, 15, 25, 100]
    labels = ["0%", "1-5%", "6-10%", "11-15%", "16-25%", "26%+"]
    work["discount_band"] = pd.cut(work["discount_pct"], bins=bins, labels=labels)
    summary = (
        work.groupby("discount_band", observed=False, as_index=False)
        .agg(sales=("sales", "sum"), estimated_profit=("estimated_profit", "sum"), transactions=("transaction_id", "nunique"))
    )
    summary["profit_margin"] = summary["estimated_profit"] / summary["sales"].replace(0, np.nan)
    correlation = float(work["discount_pct"].corr(work["profit_margin"])) if len(work) > 1 else np.nan
    return summary, correlation


def quantity_sales_correlation(frame: pd.DataFrame) -> float:
    work = frame.dropna(subset=["room_nights", "sales"])
    return float(work["room_nights"].corr(work["sales"])) if len(work) > 1 else np.nan


def product_outliers(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag high-value stay records using the IQR rule on sales."""
    work = frame.dropna(subset=["sales"]).copy()
    q1, q3 = work["sales"].quantile([0.25, 0.75])
    threshold = q3 + 1.5 * (q3 - q1)
    return (
        work.loc[work["sales"] > threshold, ["order_id", "transaction_id", "product", "region", "sales", "estimated_profit"]]
        .sort_values("sales", ascending=False)
        .head(20)
    )


def high_sales_low_profit_categories(frame: pd.DataFrame) -> pd.DataFrame:
    category = performance_by(frame, "category")
    median_sales = category["sales"].median()
    median_margin = category["profit_margin"].median()
    return category.loc[(category["sales"] >= median_sales) & (category["profit_margin"] < median_margin)].copy()


def high_orders_low_revenue_regions(frame: pd.DataFrame) -> pd.DataFrame:
    region = performance_by(frame, "region")
    median_orders = region["orders"].median()
    median_aov = region["average_order_value"].median()
    return region.loc[(region["orders"] >= median_orders) & (region["average_order_value"] < median_aov)].copy()


def _leader(table: pd.DataFrame, label: str, value: str) -> str:
    if table.empty:
        return "Not available"
    row = table.sort_values(value, ascending=False).iloc[0]
    label_value = row[label]
    if isinstance(label_value, pd.Timestamp):
        label_value = label_value.strftime("%b %Y")
    elif isinstance(label_value, (float, np.floating)) and float(label_value).is_integer():
        label_value = int(label_value)
    if value in {"sales", "estimated_profit", "average_order_value"}:
        display_value = money(row[value])
    elif value in {"sales_growth", "profit_margin"}:
        display_value = percent(row[value])
    else:
        display_value = row[value]
    return f"{label_value} ({display_value})"


def business_answers(frame: pd.DataFrame) -> pd.DataFrame:
    """Return an auditable answer table for the 25 requested business questions."""
    summary = kpis(frame)
    category = performance_by(known_records(frame, "category"), "category")
    region = performance_by(known_records(frame, "region"), "region")
    product = performance_by(known_records(frame, "product"), "product")
    segment = performance_by(known_records(frame, "customer_segment"), "customer_segment")
    channel = performance_by(known_records(frame, "sales_channel"), "sales_channel")
    monthly = monthly_sales(frame)
    yearly = yearly_sales_growth(frame)
    customers = top_customers(frame)
    discount_summary, discount_corr = discount_profit_analysis(frame)
    quantity_corr = quantity_sales_correlation(frame)
    sales_profit_corr = float(frame["sales"].corr(frame["estimated_profit"]))
    high_sales_low_profit = high_sales_low_profit_categories(known_records(frame, "category"))
    high_orders_low_revenue = high_orders_low_revenue_regions(known_records(frame, "region"))
    outliers = product_outliers(frame)

    highest_sales_month = monthly.nlargest(1, "sales")
    highest_profit_month = monthly.nlargest(1, "estimated_profit")
    highest_growth = yearly.dropna(subset=["sales_growth"]).nlargest(1, "sales_growth")
    segment_by_margin = segment.nlargest(1, "profit_margin")

    answer_rows = [
        ("1", "Total sales", money(summary["total_sales"]), "Stay revenue: room, food, spa, and other revenue."),
        ("2", "Total profit", money(summary["estimated_profit"]), "Estimated contribution profit using documented cost assumptions."),
        ("3", "Average order value", money(summary["average_order_value"]), "Total stay sales divided by unique booking orders."),
        ("4", "Total number of orders", f"{summary['orders']:,}", "Unique Booking_ID values in the stay-level sales dataset."),
        ("5", "Highest sales order", f"{summary['highest_sales_order']:,} ({money(summary['highest_sales_order_value'])})", "Highest aggregated booking sales."),
        ("6", "Category with highest sales", _leader(category, "category", "sales"), "Category is mapped to Room_Type."),
        ("7", "Category with highest profit", _leader(category, "category", "estimated_profit"), "Estimated profit, mapped to Room_Type."),
        ("8", "Region with highest sales", _leader(region, "region", "sales"), "Region is mapped to hotel City."),
        ("9", "Most profitable product", _leader(product, "product", "estimated_profit"), "Product is mapped to Hotel Name and Room Type."),
        ("10", "Most common payment mode", "Not available in the supplied data", "No payment-mode field is present. Booking channel is shown separately as a commercial proxy."),
        ("11", "Customer segment with maximum revenue", _leader(segment, "customer_segment", "sales"), "Customer segment is mapped to Loyalty_Tier."),
        ("12", "Monthly sales trend", f"{len(monthly):,} observed months", "Monthly aggregation by Checkin_Date."),
        ("13", "Best year-on-year sales growth", _leader(highest_growth, "year", "sales_growth") if not highest_growth.empty else "Not available", "Yearly sales growth from Checkin_Date."),
        ("14", "Top customer by sales", _leader(customers, "Guest_Name", "sales"), "Ranks guest revenue across stay transactions."),
        ("15", "Region with highest average order value", _leader(region, "region", "average_order_value"), "Sales divided by unique bookings for each hotel city."),
        ("16", "High-sales, low-profit category", ", ".join(high_sales_low_profit["category"].astype(str)) or "None", "Sales at or above median and margin below median."),
        ("17", "High-order, low-revenue region", ", ".join(high_orders_low_revenue["region"].astype(str)) or "None", "Orders at or above median and AOV below median."),
        ("18", "Discount relationship with profit", f"Correlation with profit margin: {discount_corr:.2f}" if pd.notna(discount_corr) else "Not available", "Association only; not a causal claim."),
        ("19", "Quantity relationship with sales", f"Correlation of room nights and sales: {quantity_corr:.2f}" if pd.notna(quantity_corr) else "Not available", "Quantity is room_nights = Nights × Rooms_Booked."),
        ("20", "Sales and profit correlation", f"{sales_profit_corr:.2f}" if pd.notna(sales_profit_corr) else "Not available", "Pearson correlation across stay transactions."),
        ("21", "Potential product outliers", f"{len(outliers):,} high-value stay records flagged", "IQR rule on stay sales; review these records before action."),
        ("22", "Month with highest sales", _leader(highest_sales_month, "month_start", "sales"), "Monthly aggregation by Checkin_Date."),
        ("23", "Month with highest profit", _leader(highest_profit_month, "month_start", "estimated_profit"), "Estimated profit aggregated by Checkin_Date."),
        ("24", "Segment with highest profit margin", _leader(segment_by_margin, "customer_segment", "profit_margin") if not segment_by_margin.empty else "Not available", "Estimated profit divided by sales."),
        ("25", "Booking channel with highest sales", _leader(channel, "sales_channel", "sales"), "Booking channel is used because payment mode is not supplied."),
    ]
    return pd.DataFrame(answer_rows, columns=["question_no", "business_question", "answer", "method"])


def narrative_insights(frame: pd.DataFrame) -> list[str]:
    """Generate concise, evidence-based callouts for the dashboard overview."""
    category = performance_by(known_records(frame, "category"), "category")
    region = performance_by(known_records(frame, "region"), "region")
    segment = performance_by(known_records(frame, "customer_segment"), "customer_segment")
    discount_summary, discount_corr = discount_profit_analysis(frame)
    points: list[str] = []

    if not category.empty:
        lead = category.iloc[0]
        points.append(
            f"{lead['category']} leads room-category sales at {money(lead['sales'])}, contributing {lead['sales'] / frame['sales'].sum():.1%} of revenue."
        )
    if not region.empty:
        best_aov = region.nlargest(1, "average_order_value").iloc[0]
        points.append(
            f"{best_aov['region']} has the highest average order value at {money(best_aov['average_order_value'])}."
        )
    if not segment.empty:
        best_margin = segment.nlargest(1, "profit_margin").iloc[0]
        points.append(
            f"{best_margin['customer_segment']} has the strongest estimated margin at {best_margin['profit_margin']:.1%}."
        )
    if pd.notna(discount_corr):
        direction = "negative" if discount_corr < 0 else "positive"
        points.append(
            f"The observed discount-to-margin relationship is {direction} (correlation {discount_corr:.2f}); it should be interpreted as association, not causation."
        )
    return points


def apply_filters(frame: pd.DataFrame, date_range: tuple[pd.Timestamp, pd.Timestamp], selections: dict[str, Iterable[str]]) -> pd.DataFrame:
    """Filter without mutating the cached master transaction dataset."""
    filtered = frame.copy()
    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    date_mask = filtered["transaction_date"].between(start_date, end_date)
    source_min = filtered["transaction_date"].min().normalize()
    source_max = filtered["transaction_date"].max().normalize()
    if start_date.normalize() <= source_min and end_date.normalize() >= source_max:
        date_mask = date_mask | filtered["transaction_date"].isna()
    filtered = filtered.loc[date_mask]
    for column, selected in selections.items():
        values = list(selected)
        if values:
            filtered = filtered.loc[filtered[column].isin(values)]
    return filtered
