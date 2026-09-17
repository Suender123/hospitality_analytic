<<<<<<< HEAD
# Hospitality Revenue Intelligence

This project is an end-to-end data analytics pipeline and interactive Streamlit dashboard built for the hospitality industry. It takes raw, disconnected operational data—such as bookings, stays, guest profiles, and reviews—and transforms it into a clean, unified dataset to extract actionable business insights.

## What this project does

Operational hotel data often lacks direct profitability metrics. This tool bridges that gap by running the raw data through a Python-based pipeline that cleans, deduplicates, and merges the records into a single source of truth. It also applies financial modeling to estimate costs and profit margins based on room types and ancillary revenue streams.

The final output is an interactive dashboard that provides:
- Executive financial summaries and key performance indicators (KPIs) in INR.
- Clear visualizations of seasonal revenue trends and room category performance.
- Deep dives into customer segments, loyalty tiers, and acquisition channels.
- Profitability diagnostics, including margin analysis and automated outlier detection for unusual transactions.
- A dedicated insights section that directly answers complex business questions with a polished layout.

## Technology Stack

- Python 3.11+
- Pandas for data manipulation and the ETL pipeline
- Plotly for interactive data visualizations
- Streamlit for the front-end dashboard interface

## Project Structure

```text
.
├── app.py                    # Main Streamlit dashboard application
├── src/
│   ├── data_pipeline.py      # Data cleaning, joining, and transformation logic
│   └── analysis.py           # Business logic, KPI calculations, and insights extraction
├── scripts/run_eda.py        # Script for reproducible data exports
├── tests/test_pipeline.py    # Unit tests for the data pipeline
├── reports/                  # Generated summary reports and figures
├── outputs/                  # Cleaned CSV datasets (ignored by Git)
└── requirements.txt          # Python dependencies
```

## How to run the project locally

1. Clone this repository to your local machine.
2. Ensure you have Python 3.11 or later installed.
3. Install the required dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. (Optional) Run the data pipeline script to generate local clean data files:
   ```bash
   python scripts/run_eda.py
   ```
5. Start the Streamlit dashboard:
   ```bash
   streamlit run app.py
   ```

The dashboard will automatically open in your default web browser at http://localhost:8501.

## Data Quality and Testing

The pipeline is designed with data integrity in mind. It standardizes identifiers, handles missing data gracefully, and maintains an internal audit log of dropped duplicates and unmatched records. 

To verify the pipeline logic, you can run the included test suite:
```bash
python -m unittest discover -s tests -v
```
=======
# hospitality_analytic
An end-to-end data analytics pipeline and interactive Streamlit dashboard that transforms raw hospitality data into actionable revenue and profitability insights.
>>>>>>> 478631f435c52ac5c574bcb670f91a2c65595b7d
