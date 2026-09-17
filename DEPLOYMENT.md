# Deployment guide

## 1. Publish the repository to GitHub

Create an empty GitHub repository named `hospitality-revenue-intelligence` without adding a README, licence, or `.gitignore`. Then run the following commands in the project folder, replacing the repository URL with your own.

```bash
git init
git add app.py src scripts tests .streamlit requirements.txt README.md DEPLOYMENT.md .gitignore
git commit -m "Build hospitality revenue intelligence dashboard"
git branch -M main
git remote add origin https://github.com/<your-account>/hospitality-revenue-intelligence.git
git push -u origin main
```

The raw CSV files are part of the analytical input. Add them to Git only if their sharing and size are appropriate for the repository. The current source files are below GitHub's 100 MB single-file limit. Do not publish data that contains restricted customer information.

## 2. Deploy on Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud with the GitHub account that owns or can access the repository.
2. Select **Create app**.
3. Choose the `hospitality-revenue-intelligence` repository and the `main` branch.
4. Set the main file path to `app.py`.
5. Select **Deploy**.

Streamlit Community Cloud installs dependencies from `requirements.txt`. Keep all required source CSV files at the repository root, or update `PROJECT_ROOT` in `src/data_pipeline.py` if you later move them to a `data/` folder.

## 3. Post-deployment check

After publishing, validate that:

- the Overview page loads without missing-data errors;
- filters update every KPI and chart;
- the CSV download returns the active filtered dataset;
- the Business answers and data tab shows 25 answers;
- the data-quality audit reports the expected 90,000 stay transactions.
