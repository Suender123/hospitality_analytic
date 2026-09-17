"""Streamlit application for hospitality revenue and profitability analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analysis import (
    apply_filters,
    business_answers,
    discount_profit_analysis,
    high_orders_low_revenue_regions,
    high_sales_low_profit_categories,
    kpis,
    monthly_sales,
    narrative_insights,
    performance_by,
    product_outliers,
    quantity_sales_correlation,
    top_customers,
    yearly_sales_growth,
)
from src.data_pipeline import PROJECT_ROOT, build_data_bundle


st.set_page_config(
    page_title="Hospitality Revenue Intelligence",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "navy": "#0B1F33",
    "teal": "#087E8B",
    "blue": "#1F77B4",
    "gold": "#D99A1A",
    "coral": "#D95D39",
    "slate": "#526777",
    "background": "#F7F9FC",
}


@st.cache_data(show_spinner="Preparing the hospitality analytics dataset...")
def load_bundle():
    return build_data_bundle(PROJECT_ROOT)


def format_currency(value: float) -> str:
    return f"₹{value:,.0f}"


def clean_plot(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=20),
        font=dict(family="Arial, sans-serif", color=COLORS["navy"]),
        title=dict(font=dict(size=18, color=COLORS["navy"], family="Arial, sans-serif")),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F0F4F8", linecolor="#DCE3EA")
    fig.update_yaxes(showgrid=True, gridcolor="#F0F4F8", zerolinecolor="#DCE3EA")
    return fig


def sidebar_filters(frame: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Analysis filters")
    min_date = frame["transaction_date"].min().date()
    max_date = frame["transaction_date"].max().date()
    selected_dates = st.sidebar.date_input(
        "Stay date", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    filter_fields = {
        "region": "Hotel city",
        "Hotel_Type": "Hotel type",
        "category": "Room category",
        "sales_channel": "Booking channel",
        "customer_segment": "Loyalty tier",
        "Status": "Booking status",
    }
    selections: dict[str, list[str]] = {}
    for column, label in filter_fields.items():
        options = sorted(frame[column].dropna().astype(str).unique().tolist())
        selections[column] = st.sidebar.multiselect(label, options)

    filtered = apply_filters(
        frame,
        (pd.Timestamp(start_date), pd.Timestamp(end_date)),
        selections,
    )
    st.sidebar.caption(f"{len(filtered):,} stay transactions in the current view")
    return filtered


def render_overview(frame: pd.DataFrame) -> None:
    current_kpis = kpis(frame)
    with st.container():
        first, second, third, fourth, fifth = st.columns(5)
        first.metric("Total Sales", format_currency(current_kpis["total_sales"]))
        second.metric("Estimated Profit", format_currency(current_kpis["estimated_profit"]))
        third.metric("Profit Margin", f"{current_kpis['profit_margin']:.1%}")
        fourth.metric("Orders", f"{current_kpis['orders']:,}")
        fifth.metric("Average Order Value", format_currency(current_kpis["average_order_value"]))
        
        st.caption(
            "Sales are recognised from completed stay revenue. Profit is an estimated contribution measure using transparent room-type and ancillary cost assumptions."
        )

    st.divider()

    monthly = monthly_sales(frame)
    category = performance_by(frame, "category")
    
    with st.container():
        left, right = st.columns((1.45, 1))
        with left:
            figure = px.line(
                monthly,
                x="month_start",
                y=["sales", "estimated_profit"],
                title="Monthly Sales and Estimated Profit Trend",
                labels={"value": "Amount (INR)", "month_start": "Stay month", "variable": "Metric"},
                color_discrete_map={"sales": COLORS["teal"], "estimated_profit": COLORS["gold"]},
                markers=True,
            )
            figure.update_yaxes(separatethousands=True)
            figure.update_traces(hovertemplate="%{y:,.0f} INR<extra></extra>")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Tracking revenue vs profit over time to identify seasonal peaks and troughs.")
        with right:
            figure = px.bar(
                category.sort_values("sales"),
                x="sales",
                y="category",
                orientation="h",
                title="Sales by Room Category",
                color="category",
                color_discrete_sequence=[COLORS["teal"], COLORS["blue"], COLORS["gold"]],
                text_auto=".2s",
            )
            figure.update_layout(showlegend=False)
            figure.update_xaxes(separatethousands=True, title="Sales (INR)")
            figure.update_yaxes(title="")
            figure.update_traces(textposition="outside", hovertemplate="Sales: %{x:,.0f} INR<extra></extra>")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Identifies which room categories drive the most overall revenue volume.")

    st.divider()
    
    with st.container():
        st.subheader("Commercial Signals")
        insights = narrative_insights(frame)
        if insights:
            for insight in insights:
                st.info(insight, icon="💡")

        product = performance_by(frame, "product", top_n=40)
        figure = px.scatter(
            product,
            x="sales",
            y="estimated_profit",
            size="orders",
            color="profit_margin",
            hover_name="product",
            color_continuous_scale="Tealgrn",
            title="Product Performance Matrix (Sales vs Profit)",
            labels={"sales": "Sales (INR)", "estimated_profit": "Estimated Profit (INR)", "profit_margin": "Margin"},
        )
        figure.update_xaxes(separatethousands=True)
        figure.update_yaxes(separatethousands=True)
        figure.update_traces(hovertemplate="<b>%{hovertext}</b><br>Sales: %{x:,.0f} INR<br>Profit: %{y:,.0f} INR<extra></extra>")
        st.plotly_chart(clean_plot(figure, height=450), use_container_width=True)
        st.caption("Insight: Bubble size represents order volume; color intensity represents profit margin. Ideal products appear in the top right (High Sales, High Profit).")


def render_market_and_customers(frame: pd.DataFrame) -> None:
    region = performance_by(frame, "region", top_n=12)
    segment = performance_by(frame, "customer_segment")
    channel = performance_by(frame, "sales_channel")
    customers = top_customers(frame)

    with st.container():
        left, right = st.columns(2)
        with left:
            figure = px.bar(
                region.sort_values("sales"),
                x="sales",
                y="region",
                orientation="h",
                color="profit_margin",
                color_continuous_scale="Blues",
                title="Hotel City Sales and Profitability",
                labels={"sales": "Sales (INR)", "region": "Hotel City", "profit_margin": "Margin"},
                text_auto=".2s",
            )
            figure.update_xaxes(separatethousands=True)
            figure.update_traces(textposition="outside", hovertemplate="%{y}: %{x:,.0f} INR<extra></extra>")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Evaluate geographic performance. Darker blue indicates a higher profit margin.")
        with right:
            figure = px.bar(
                segment.sort_values("sales"),
                x="customer_segment",
                y=["sales", "estimated_profit"],
                barmode="group",
                title="Revenue and Profit by Loyalty Tier",
                labels={"value": "Amount (INR)", "customer_segment": "Loyalty Tier", "variable": "Metric"},
                color_discrete_map={"sales": COLORS["blue"], "estimated_profit": COLORS["gold"]},
                text_auto=".2s",
            )
            figure.update_yaxes(separatethousands=True)
            figure.update_traces(textposition="outside")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Identify which customer segments are driving the most value.")

    st.divider()

    with st.container():
        left, right = st.columns((1.2, 1))
        with left:
            display_customers = customers[["Guest_Name", "customer_segment", "sales", "estimated_profit", "orders"]].copy()
            display_customers.rename(
                columns={
                    "Guest_Name": "Customer",
                    "customer_segment": "Loyalty Tier",
                    "sales": "Sales (INR)",
                    "estimated_profit": "Estimated Profit (INR)",
                    "orders": "Orders",
                },
                inplace=True,
            )
            st.subheader("Top Customers by Sales")
            st.dataframe(
                display_customers.style.format({"Sales (INR)": "₹{:,.0f}", "Estimated Profit (INR)": "₹{:,.0f}"}),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("Insight: Detailed view of top-spending guests and their associated profitability.")
        with right:
            figure = px.pie(
                channel,
                values="sales",
                names="sales_channel",
                hole=0.55,
                title="Sales Mix by Booking Channel",
                color_discrete_sequence=[COLORS["teal"], COLORS["blue"], COLORS["gold"]],
            )
            figure.update_traces(hovertemplate="%{label}<br>Sales: %{value:,.0f} INR<br>Share: %{percent}<extra></extra>")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Breakdown of revenue by acquisition channel.")



def render_profitability(frame: pd.DataFrame) -> None:
    category = performance_by(frame, "category")
    discount, discount_correlation = discount_profit_analysis(frame)
    outliers = product_outliers(frame)
    high_sales_low_profit = high_sales_low_profit_categories(frame)
    high_orders_low_revenue = high_orders_low_revenue_regions(frame)

    with st.container():
        left, right = st.columns(2)
        with left:
            figure = px.bar(
                category,
                x="category",
                y=["sales", "estimated_profit"],
                barmode="group",
                title="Category Sales vs Estimated Profit",
                labels={"value": "Amount (INR)", "category": "Room Category", "variable": "Metric"},
                color_discrete_map={"sales": COLORS["teal"], "estimated_profit": COLORS["coral"]},
                text_auto=".2s",
            )
            figure.update_yaxes(separatethousands=True)
            figure.update_traces(textposition="outside")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption("Insight: Compares top-line revenue to bottom-line estimated profit by room category.")
        with right:
            figure = px.bar(
                discount,
                x="discount_band",
                y="profit_margin",
                color="profit_margin",
                color_continuous_scale="RdYlGn",
                title="Estimated Profit Margin by Discount Band",
                labels={"discount_band": "Discount Band", "profit_margin": "Estimated Profit Margin"},
                text_auto=".1%",
            )
            figure.update_layout(showlegend=False, coloraxis_showscale=False)
            figure.update_yaxes(tickformat=".0%")
            figure.update_traces(textposition="outside")
            st.plotly_chart(clean_plot(figure), use_container_width=True)
            st.caption(f"Insight: Discount percentage and profit margin correlation: {discount_correlation:.2f}. Notice how bands above 15% sharply erode margins.")

    st.divider()

    with st.container():
        quantity_correlation = quantity_sales_correlation(frame)
        sample_size = min(len(frame), 5_000)
        sample = frame.sample(sample_size, random_state=42) if len(frame) > sample_size else frame
        figure = px.scatter(
            sample,
            x="room_nights",
            y="sales",
            color="category",
            opacity=0.55,
            title=f"Room Nights vs Sales (Correlation: {quantity_correlation:.2f})",
            labels={"room_nights": "Room Nights", "sales": "Sales (INR)", "category": "Room Category"},
            color_discrete_sequence=[COLORS["teal"], COLORS["blue"], COLORS["gold"]],
        )
        figure.update_yaxes(separatethousands=True)
        figure.update_traces(hovertemplate="Room Nights: %{x}<br>Sales: %{y:,.0f} INR<extra></extra>")
        st.plotly_chart(clean_plot(figure, height=410), use_container_width=True)
        st.caption("Insight: Verifies that longer stays and more rooms booked proportionally increase revenue.")

    st.divider()

    with st.container():
        left, right = st.columns(2)
        with left:
            st.subheader("High Sales but Low Margin")
            if high_sales_low_profit.empty:
                st.success("Great! No category meets the high-sales but below-median-margin condition.")
            else:
                st.dataframe(
                    high_sales_low_profit[["category", "sales", "estimated_profit", "profit_margin"]].style.format(
                        {"sales": "₹{:,.0f}", "estimated_profit": "₹{:,.0f}", "profit_margin": "{:.1%}"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption("Insight: These categories generate high volume but are less efficient at producing profit.")
        with right:
            st.subheader("High Order Volume, Lower AOV")
            if high_orders_low_revenue.empty:
                st.success("Great! No region meets the high-order but below-median-AOV condition.")
            else:
                st.dataframe(
                    high_orders_low_revenue[["region", "orders", "sales", "average_order_value"]].style.format(
                        {"sales": "₹{:,.0f}", "average_order_value": "₹{:,.0f}"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption("Insight: These regions take a lot of work (many orders) for a lower average return.")

    st.divider()
    
    with st.container():
        st.subheader("Potential High-Value Transaction Outliers")
        if outliers.empty:
            st.success("No high-value stay record exceeds the current IQR outlier threshold.")
        else:
            st.dataframe(
                outliers.style.format({"sales": "₹{:,.0f}", "estimated_profit": "₹{:,.0f}"}),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("Insight: IQR-based flags identify transactions for review. These are high-value anomalies (not necessarily errors).")


def render_answers_and_data(frame: pd.DataFrame, quality: pd.DataFrame) -> None:
    answers = business_answers(frame)
    st.subheader("Executive Insights")
    st.caption("Key business takeaways generated from the current data filters.")
    
    # Display insights as a polished grid of cards
    cols = st.columns(3)
    for idx, row in enumerate(answers.itertuples()):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{row.business_question}**")
                st.markdown(f"### {row.answer}")
                st.caption(f"{row.method}")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Dataset Mapping & Method")
        mapping = pd.DataFrame(
            [
                ("Sales", "Room_Revenue + Food_Revenue + Spa_Revenue + Other_Revenue"),
                ("Order", "Booking_ID represented by a stay transaction"),
                ("Category", "Room_Type"),
                ("Region", "Hotel City"),
                ("Customer segment", "Loyalty_Tier"),
                ("Product", "Hotel_Name and Room_Type"),
                ("Quantity", "Nights × Rooms_Booked"),
                ("Payment mode", "Not supplied; Booking Channel is reported separately"),
                ("Profit", "Estimated contribution profit using documented room and ancillary cost assumptions"),
            ],
            columns=["Business Concept", "Source Mapping or Calculation"],
        )
        st.dataframe(mapping, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Data Quality Audit")
        st.dataframe(quality.fillna(""), use_container_width=True, hide_index=True)

    st.divider()
    
    st.subheader("Filtered Analytical Data")
    export_columns = [
        "order_id",
        "transaction_date",
        "Hotel_Name",
        "region",
        "Guest_Name",
        "customer_segment",
        "category",
        "sales_channel",
        "room_nights",
        "discount_pct",
        "sales",
        "estimated_profit",
        "profit_margin",
    ]
    preview = frame[export_columns].sort_values("transaction_date", ascending=False)
    st.dataframe(preview.head(500), use_container_width=True, hide_index=True)
    st.download_button(
        "Download Filtered Analytical Data",
        data=preview.to_csv(index=False).encode("utf-8"),
        file_name="filtered_hospitality_transactions.csv",
        mime="text/csv",
    )


def main() -> None:
    bundle = load_bundle()
    frame = sidebar_filters(bundle.transactions)

    st.title("Hospitality Revenue Intelligence")
    st.write("An interactive view of stay revenue, estimated profitability, customers, channels, and operational commercial signals.")

    if frame.empty:
        st.warning("No transactions match the active filters. Adjust the filters to continue.")
        return

    overview_tab, market_tab, profitability_tab, answers_tab = st.tabs(
        ["Overview", "Market and Customers", "Profitability", "Key Insights & Data"]
    )
    with overview_tab:
        render_overview(frame)
    with market_tab:
        render_market_and_customers(frame)
    with profitability_tab:
        render_profitability(frame)
    with answers_tab:
        render_answers_and_data(frame, bundle.quality)

if __name__ == "__main__":
    main()
