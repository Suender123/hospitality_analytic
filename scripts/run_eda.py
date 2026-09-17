"""Run the reproducible EDA workflow and export interactive Plotly artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.analysis import (
    business_answers,
    discount_profit_analysis,
    kpis,
    monthly_sales,
    performance_by,
    yearly_sales_growth,
)
from src.data_pipeline import PROJECT_ROOT, build_data_bundle, export_clean_dataset


REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

PALETTE = ["#087E8B", "#1F77B4", "#D99A1A", "#D95D39"]


def save_figure(figure, filename: str) -> None:
    figure.update_layout(
        template="plotly_white",
        font=dict(family="Arial, sans-serif", color="#0B1F33"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=20, t=55, b=35),
    )
    figure.write_html(FIGURE_DIR / filename, include_plotlyjs="cdn")


def build_report() -> Path:
    """Create cleaned data, interactive visuals, a question table, and a narrative EDA report."""
    REPORT_DIR.mkdir(exist_ok=True)
    FIGURE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    bundle = build_data_bundle(PROJECT_ROOT)
    transactions = bundle.transactions
    export_clean_dataset(OUTPUT_DIR / "cleaned_hospitality_transactions.csv", PROJECT_ROOT)

    monthly = monthly_sales(transactions)
    yearly = yearly_sales_growth(transactions)
    category = performance_by(transactions, "category")
    region = performance_by(transactions, "region", top_n=12)
    product = performance_by(transactions, "product", top_n=40)
    discount, discount_correlation = discount_profit_analysis(transactions)

    monthly_chart = px.line(
        monthly,
        x="month_start",
        y=["sales", "estimated_profit"],
        title="Monthly Sales and Estimated Profit",
        labels={"value": "Currency units", "month_start": "Stay month", "variable": "Metric"},
        color_discrete_sequence=PALETTE[:2],
    )
    save_figure(monthly_chart, "monthly_sales_profit.html")

    category_chart = px.bar(
        category.sort_values("sales"),
        x="sales",
        y="category",
        orientation="h",
        title="Sales by Room Category",
        labels={"sales": "Currency units", "category": "Room category"},
        color="category",
        color_discrete_sequence=PALETTE,
    )
    category_chart.update_layout(showlegend=False)
    save_figure(category_chart, "category_sales.html")

    region_chart = px.bar(
        region.sort_values("sales"),
        x="sales",
        y="region",
        orientation="h",
        title="Hotel City Sales and Margin",
        labels={"sales": "Currency units", "region": "Hotel city", "profit_margin": "Profit margin"},
        color="profit_margin",
        color_continuous_scale="Blues",
    )
    save_figure(region_chart, "regional_sales.html")

    product_chart = px.scatter(
        product,
        x="sales",
        y="estimated_profit",
        size="orders",
        color="profit_margin",
        hover_name="product",
        title="Product Sales and Estimated Profit",
        labels={"sales": "Currency units", "estimated_profit": "Currency units", "profit_margin": "Profit margin"},
        color_continuous_scale="Tealgrn",
    )
    save_figure(product_chart, "product_profitability.html")

    discount_chart = px.bar(
        discount,
        x="discount_band",
        y="profit_margin",
        title="Estimated Profit Margin by Discount Band",
        labels={"discount_band": "Discount band", "profit_margin": "Profit margin"},
        color="profit_margin",
        color_continuous_scale="RdYlGn",
    )
    discount_chart.update_yaxes(tickformat=".0%")
    save_figure(discount_chart, "discount_margin.html")

    answers = business_answers(transactions)
    answers.to_csv(OUTPUT_DIR / "business_question_answers.csv", index=False)
    summary = kpis(transactions)
    leader_category = category.iloc[0]
    leader_region = region.iloc[0]
    best_growth = yearly.dropna(subset=["sales_growth"]).nlargest(1, "sales_growth")
    growth_text = "Not available"
    if not best_growth.empty:
        growth_text = f"{int(best_growth.iloc[0]['year'])}: {best_growth.iloc[0]['sales_growth']:.1%}"

    report = f"""# Hospitality Revenue Intelligence: EDA Summary

## Scope

The analysis combines the supplied booking, stay, hotel, guest, review, staff, and marketing files. The commercial grain is one stay transaction linked to a booking. The source data contains no currency code, so all monetary values are labelled as **currency units**.

## Headline results

| Metric | Result |
| --- | ---: |
| Total sales | {summary['total_sales']:,.0f} |
| Estimated profit | {summary['estimated_profit']:,.0f} |
| Estimated profit margin | {summary['profit_margin']:.1%} |
| Unique booking orders | {summary['orders']:,} |
| Average order value | {summary['average_order_value']:,.0f} |

## Findings

- **{leader_category['category']}** is the highest-sales room category, with {leader_category['sales']:,.0f} in sales.
- **{leader_region['region']}** has the highest sales among hotel cities, at {leader_region['sales']:,.0f}.
- The strongest observed year-on-year sales growth is **{growth_text}**.
- The correlation between discount percentage and estimated profit margin is **{discount_correlation:.2f}**. This measures association only and does not establish causality.

## Business definitions

- **Sales:** Room_Revenue + Food_Revenue + Spa_Revenue + Other_Revenue.
- **Order:** unique Booking_ID associated with a stay transaction.
- **Category:** Room_Type.
- **Region:** hotel City.
- **Customer segment:** Loyalty_Tier.
- **Product:** Hotel_Name and Room_Type.
- **Quantity:** Nights × Rooms_Booked.
- **Profit:** estimated contribution profit. The source data has no cost or profit field, so the model applies documented room-type contribution margins and ancillary cost rates. This must be replaced with actual finance costs before any financial decision is made.
- **Payment mode:** not present in the source data. Booking channel is analysed as an acquisition channel, not a payment method.

## Delivered files

- `outputs/cleaned_hospitality_transactions.csv` contains the cleaned and transformed analytical table.
- `outputs/business_question_answers.csv` contains answers to all 25 requested questions.
- `reports/figures/` contains standalone interactive Plotly charts.
"""
    report_path = REPORT_DIR / "business_insights.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


if __name__ == "__main__":
    created_report = build_report()
    print(f"EDA report written to {created_report}")
