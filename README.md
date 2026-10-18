Mamaearth Returns & Growth Intelligence Pipeline
This repository contains the complete Mamaearth capstone project for the Data Analytics with AI & Gen AI program. It has three connected layers:
1.	SQL relational layer: creates the SQLite database, loads the raw CSV data, and runs the required reports.
2.	Python/Pandas analysis layer: independently reads the same raw CSV files, cleans and analyzes them, prints every required intermediate result, and creates the two visualizations.
3.	GenAI insight narrator: receives the verified Part 1/Part 2 findings and produces a Situation–Complication–Resolution narrative using Gemini, with a fully offline fallback.
The raw CSV files are committed unchanged. Cleaning is performed in Python, never by editing the source data.
Repository structure
text
.
├── README.md
├── requirements.txt
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json
    ├── export_findings.py
    ├── generate_narrative.py
    ├── sample_output.txt
    └── __init__.py
Requirements
Use Python 3.10 or newer, SQLite 3, and a terminal.
Install the Python dependencies from the repository root:
Bash
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Run the complete pipeline in order
1. Run the SQL relational layer
Start from a fresh database so that the ALTER TABLE statement in the final SQL report is repeatable:
Bash
rm -f data/mamaearth.db
sqlite3 data/mamaearth.db < sql/schema.sql
sqlite3 data/mamaearth.db < sql/seed_data.sql
sqlite3 data/mamaearth.db < sql/reports.sql
This executes the layers in the required order:
•	schema.sql creates customers, products, and orders with primary keys, foreign keys, required constraints, and nullable discount_pct/rating fields.
•	seed_data.sql loads the three unchanged CSV files and converts blank discount/rating cells into SQL NULL.
•	reports.sql runs the required reports and adds/populates customers.loyalty_tier.
The SQL layer verifies the raw dataset values, including 45 customers, 16 products, 180 orders, raw revenue of 99,860.20, 15 unrated orders, the zero-order customer C045, city return rates, customer rankings, category revenue, acquisition sources, and Gold/Silver loyalty counts.
A convenience script performs the same work with additional validation checks:
Bash
bash scripts/rebuild_database.sh
2. Run the independent Python/Pandas Part 2 layer
Part 2 intentionally reads the CSV files directly, not the SQLite database. This allows Part 1 and Part 2 to run independently while using the same source data.
Bash
python analysis/clean_and_eda.py
python analysis/visualize.py
clean_and_eda.py prints all intermediate results required by the brief. It standardizes payment methods, removes the five natural-key duplicates, imputes missing values, merges products and customers, computes order_value, reconciles the cleaned total to Part 1, flags quantity outliers, analyzes COD returns and city tiers, prints correlation bands, and prints both monthly time series.
At the end of the analysis run, the script calls narrator/export_findings.py and writes narrator/findings.json. This JSON is generated from the cleaned Part 2 dataframe; it is not manually typed. It contains the verified figures required by Part 3:
•	Cleaned revenue: 97,358.30
•	Raw revenue: 99,860.20
•	Duplicate reconciliation delta: 2,501.90
•	COD return rate: 44.4%
•	COD + Tier-2 return rate: 54.5%
•	True peak: March 2026 at 20,318.90
•	January apparent revenue: 29,582.10; corrected revenue: 11,637.10
visualize.py rebuilds both PNG files from the raw CSVs. The payment chart is descending and labels each percentage; its title states the COD finding. The monthly chart uses the outlier-corrected series and names the true peak month.
3. Run the Part 3 Gemini narrator
Google AI Studio provides a free Gemini API key and free usage tier. Never commit the key to GitHub. Set it as an environment variable only in your local terminal:
Linux/macOS:
Bash
export GEMINI_API_KEY="your_google_ai_studio_key"
python narrator/generate_narrative.py
Windows PowerShell:
powershell
$env:GEMINI_API_KEY = "your_google_ai_studio_key"
python narrator/generate_narrative.py
The online function uses from google import genai and client.models.generate_content(...). It supplies a separate system instruction defining the senior data analyst role, the three SCR sections, and the no-invented-statistics rule. The user prompt is built from the loaded findings dictionary. The request uses temperature 0.0, an explicit maximum of 500 output tokens, and a 30-second timeout.
4. Run the fully offline path with no API key
The project is gradable with no network access and no API key. In a fresh terminal, simply run:
Bash
unset GEMINI_API_KEY GOOGLE_API_KEY       # Linux/macOS
python narrator/generate_narrative.py
On Windows PowerShell, remove the variables if they are set:
powershell
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
python narrator/generate_narrative.py
When no key is configured, generate_scr_narrative() calls the deterministic generate_scr_narrative_offline(findings) template. If a Gemini request fails, the same fallback is used automatically. The offline path performs no network call and returns the same structured result shape.
The script prints a pass/fail line for each required numeric figure and an overall result. narrator/sample_output.txt contains a saved keyless sample with all checks passing, so grading does not depend on a live API call.
Reproducibility and safety
Run the SQL database rebuild before the SQL reports whenever starting from a fresh checkout. Run the Python analysis before the narrator so that findings.json is regenerated from the raw CSVs. Do not edit the CSVs, findings.json, or chart outputs manually to change values.
