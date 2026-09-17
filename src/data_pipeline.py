"""Clean, join, and enrich the hospitality source files for analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILES = {
    "bookings": "bookings.csv",
    "guests": "guests.csv",
    "hotels": "hotels.csv",
    "hotel_staff": "hotel_staff.csv",
    "marketing_channels": "marketing_channels.csv",
    "reviews": "reviews.csv",
    "stays": "stays.csv",
}

DATE_COLUMNS = {
    "bookings": ["Booking_Date", "Checkin_Date"],
    "guests": ["Signup_Date"],
    "marketing_channels": ["Campaign_Date"],
    "reviews": ["Review_Date"],
    "stays": ["Checkin_Date", "Checkout_Date"],
}

ROOM_MARGIN = {
    "Standard": 0.42,
    "Deluxe": 0.48,
    "Suite": 0.55,
}


@dataclass
class DataBundle:
    """The cleaned transaction dataset and supporting operational datasets."""

    transactions: pd.DataFrame
    marketing: pd.DataFrame
    staff: pd.DataFrame
    quality: pd.DataFrame


def _standardize_ids(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert identifier columns to nullable integer values without changing IDs."""
    result = frame.copy()
    for column in columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce").round().astype("Int64")
    return result


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _clean_text(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column in result:
            result[column] = result[column].astype("string").str.strip()
            result.loc[result[column].eq(""), column] = pd.NA
    return result


def _read_source_files(data_dir: Path) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]]]:
    """Read all source files and retain a compact audit log of source row counts."""
    raw: dict[str, pd.DataFrame] = {}
    audit: list[dict[str, Any]] = []

    for name, filename in SOURCE_FILES.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Required source file is missing: {path.name}")
        frame = pd.read_csv(path, low_memory=False)
        raw[name] = frame
        audit.append(
            {
                "dataset": name,
                "stage": "source",
                "rows": len(frame),
                "columns": len(frame.columns),
                "duplicate_key_rows_removed": 0,
            }
        )
    return raw, audit


def _parse_dates(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    parsed: dict[str, pd.DataFrame] = {}
    for name, frame in raw.items():
        result = frame.copy()
        for column in DATE_COLUMNS.get(name, []):
            if column in result:
                result[column] = pd.to_datetime(result[column], errors="coerce")
        parsed[name] = result
    return parsed


def _deduplicate(frame: pd.DataFrame, key: str, dataset_name: str, audit: list[dict[str, Any]]) -> pd.DataFrame:
    duplicate_rows = int(frame.duplicated(subset=[key], keep="first").sum())
    result = frame.drop_duplicates(subset=[key], keep="first").copy()
    audit.append(
        {
            "dataset": dataset_name,
            "stage": "deduplicated",
            "rows": len(result),
            "columns": len(result.columns),
            "duplicate_key_rows_removed": duplicate_rows,
        }
    )
    return result


def _prepare_sources(raw: dict[str, pd.DataFrame], audit: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    """Apply type corrections, text hygiene, and key-level deduplication."""
    parsed = _parse_dates(raw)

    bookings = _standardize_ids(parsed["bookings"], ["Booking_ID", "Guest_ID", "Hotel_ID"])
    bookings = _coerce_numeric(bookings, ["Nights", "Rooms_Booked", "Room_Rate", "Discount_Pct"])
    bookings = _clean_text(bookings, ["Channel", "Status"])
    bookings["Discount_Pct"] = bookings["Discount_Pct"].clip(lower=0, upper=100).fillna(0)
    bookings = _deduplicate(bookings, "Booking_ID", "bookings", audit)

    guests = _standardize_ids(parsed["guests"], ["Guest_ID"])
    guests = _coerce_numeric(guests, ["Age"])
    guests = _clean_text(guests, ["Guest_Name", "Country", "City", "Loyalty_Tier"])
    guests = _deduplicate(guests, "Guest_ID", "guests", audit)

    hotels = _standardize_ids(parsed["hotels"], ["Hotel_ID"])
    hotels = _coerce_numeric(hotels, ["Star_Rating", "Rooms", "Base_Room_Rate"])
    hotels = _clean_text(hotels, ["Hotel_Name", "City", "Hotel_Type"])
    hotels = _deduplicate(hotels, "Hotel_ID", "hotels", audit)

    stays = _standardize_ids(parsed["stays"], ["Stay_ID", "Booking_ID"])
    stays = _coerce_numeric(stays, ["Room_Revenue", "Food_Revenue", "Spa_Revenue", "Other_Revenue"])
    stays = _clean_text(stays, ["Room_Type"])
    stays = _deduplicate(stays, "Stay_ID", "stays", audit)

    reviews = _standardize_ids(parsed["reviews"], ["Review_ID", "Booking_ID"])
    reviews = _coerce_numeric(reviews, ["Cleanliness", "Service", "Location", "Value", "Overall_Rating"])
    reviews = _clean_text(reviews, ["Sentiment"])
    reviews = _deduplicate(reviews, "Review_ID", "reviews", audit)

    staff = _standardize_ids(parsed["hotel_staff"], ["Staff_ID", "Hotel_ID"])
    staff = _coerce_numeric(staff, ["Monthly_Salary"])
    staff = _clean_text(staff, ["Department", "Role", "Shift"])
    staff = _deduplicate(staff, "Staff_ID", "hotel_staff", audit)

    marketing = _standardize_ids(parsed["marketing_channels"], ["Channel_ID"])
    marketing = _coerce_numeric(marketing, ["Spend", "Impressions", "Clicks", "Bookings_Attributed"])
    marketing = _clean_text(marketing, ["Channel_Name"])
    marketing = _deduplicate(marketing, "Channel_ID", "marketing_channels", audit)

    return {
        "bookings": bookings,
        "guests": guests,
        "hotels": hotels,
        "stays": stays,
        "reviews": reviews,
        "staff": staff,
        "marketing": marketing,
    }


def _review_rollup(reviews: pd.DataFrame) -> pd.DataFrame:
    """Aggregate review data at booking level to preserve one transaction per stay."""
    return (
        reviews.groupby("Booking_ID", as_index=False, dropna=False)
        .agg(
            review_count=("Review_ID", "nunique"),
            avg_overall_rating=("Overall_Rating", "mean"),
            avg_cleanliness=("Cleanliness", "mean"),
            avg_service=("Service", "mean"),
            positive_review_share=("Sentiment", lambda values: (values == "Positive").mean()),
        )
    )


def _build_transactions(data: dict[str, pd.DataFrame], audit: list[dict[str, Any]]) -> pd.DataFrame:
    """Create a stay-level sales table with transparent derived commercial fields."""
    reviews = _review_rollup(data["reviews"])
    transactions = data["stays"].merge(
        data["bookings"], on="Booking_ID", how="left", suffixes=("", "_booking"), validate="m:1"
    )
    transactions = transactions.merge(data["hotels"], on="Hotel_ID", how="left", validate="m:1")
    guests_lookup = data["guests"].rename(columns={"City": "Guest_City"})
    transactions = transactions.merge(guests_lookup, on="Guest_ID", how="left", validate="m:1")
    transactions = transactions.merge(reviews, on="Booking_ID", how="left", validate="m:1")

    revenue_columns = ["Room_Revenue", "Food_Revenue", "Spa_Revenue", "Other_Revenue"]
    transactions[revenue_columns] = transactions[revenue_columns].fillna(0).clip(lower=0)
    transactions["sales"] = transactions[revenue_columns].sum(axis=1)
    transactions["order_id"] = transactions["Booking_ID"]
    transactions["transaction_id"] = transactions["Stay_ID"]
    transactions["transaction_date"] = transactions["Checkin_Date"]
    transactions["room_nights"] = (transactions["Nights"] * transactions["Rooms_Booked"]).clip(lower=0)
    transactions["discount_pct"] = transactions["Discount_Pct"].fillna(0).clip(lower=0, upper=100)

    discount_factor = (1 - transactions["discount_pct"] / 100).clip(lower=0.01)
    transactions["estimated_discount_value"] = transactions["Room_Revenue"] / discount_factor - transactions["Room_Revenue"]
    transactions["room_contribution_margin"] = transactions["Room_Type"].map(ROOM_MARGIN).fillna(0.45)

    room_cost = transactions["Room_Revenue"] * (1 - transactions["room_contribution_margin"])
    food_cost = transactions["Food_Revenue"] * 0.63
    spa_cost = transactions["Spa_Revenue"] * 0.40
    other_cost = transactions["Other_Revenue"] * 0.58
    discount_absorption = transactions["estimated_discount_value"] * 0.20
    transactions["estimated_cost"] = room_cost + food_cost + spa_cost + other_cost + discount_absorption
    transactions["estimated_profit"] = transactions["sales"] - transactions["estimated_cost"]
    transactions["profit_margin"] = np.where(
        transactions["sales"].gt(0), transactions["estimated_profit"] / transactions["sales"], np.nan
    )

    transactions["category"] = transactions["Room_Type"].fillna("Unknown")
    transactions["region"] = transactions["City"].fillna("Unknown")
    transactions["customer_segment"] = transactions["Loyalty_Tier"].fillna("Unknown")
    transactions["sales_channel"] = transactions["Channel"].fillna("Unknown")
    transactions["product"] = (
        transactions["Hotel_Name"].fillna("Unknown hotel") + " | " + transactions["category"].astype(str)
    )
    transactions["year"] = transactions["transaction_date"].dt.year.astype("Int64")
    transactions["month_start"] = transactions["transaction_date"].dt.to_period("M").dt.to_timestamp()
    transactions["month_label"] = transactions["transaction_date"].dt.strftime("%b")
    transactions["review_count"] = transactions["review_count"].fillna(0).astype(int)

    missing_booking_match = int(transactions["Hotel_ID"].isna().sum())
    missing_hotel_match = int(transactions["Hotel_Name"].isna().sum())
    missing_guest_match = int(transactions["Guest_Name"].isna().sum())
    audit.append(
        {
            "dataset": "transactions",
            "stage": "analytical_join",
            "rows": len(transactions),
            "columns": len(transactions.columns),
            "duplicate_key_rows_removed": 0,
            "missing_booking_match": missing_booking_match,
            "missing_hotel_match": missing_hotel_match,
            "missing_guest_match": missing_guest_match,
        }
    )
    return transactions


def build_data_bundle(data_dir: str | Path | None = None) -> DataBundle:
    """Build the complete analytical dataset from the supplied raw CSV files."""
    source_dir = Path(data_dir) if data_dir else PROJECT_ROOT
    raw, audit = _read_source_files(source_dir)
    cleaned = _prepare_sources(raw, audit)
    transactions = _build_transactions(cleaned, audit)
    return DataBundle(
        transactions=transactions,
        marketing=cleaned["marketing"],
        staff=cleaned["staff"],
        quality=pd.DataFrame(audit),
    )


def export_clean_dataset(output_path: str | Path, data_dir: str | Path | None = None) -> Path:
    """Export a reusable cleaned transaction table for external analysis."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_data_bundle(data_dir)
    bundle.transactions.to_csv(output, index=False)
    return output
