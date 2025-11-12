heavyRAIN – Data Retrieval Notebooks

This repo contains Jupyter notebooks for retrieving and visualizing IoT rain data from the heavyRAIN API.

Quick start:

1. Set up this notebooks project:
   python -m venv .venv
   . .\.venv\Scripts\Activate.ps1        (on Windows PowerShell)
   pip install --upgrade pip
   pip install -r requirements.txt

2. Then open http://localhost:8030/heavyrain/data-api/api/docs and check that your token works using the Authorize button.

3. Configure your API connection:
   Option A: create a .env file at the repo root
      IOT_API_BASE=http://localhost:8030
      IOT_API_TOKEN=<your_token_here>

   Option B: hard-code the values directly in utils/iot_client.py

4. Run the notebooks:
   jupyter notebook
   Then open notebooks/iot_data_examples.ipynb

Notebook details:

- Example 1: Queries IoT rain data for Bochum (Oct 1–7, 2025) with only_with_known_location=True and no pagination.
- Example 2: Same time window with pagination enabled (PAGE=500, offset loop).
- The notebook converts timestamps and numeric fields for plotting and shows rain_value trends.

Project structure:

notebooks/
  iot_data_examples.ipynb
utils/
  iot_client.py
config/
  (optional) .env
requirements.txt
.gitignore
README.md

Common issues:

- 401/403 errors → check your token in .env or Swagger UI.
- Connection errors → API server not running
- Empty results → no data for selected city or date range.
- TypeError: no numeric data to plot → handled automatically when converting rain_value.

