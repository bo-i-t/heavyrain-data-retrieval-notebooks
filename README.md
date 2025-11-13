# heavyRAIN – Data Retrieval Notebooks

This repo contains Jupyter notebooks with examples for retrieving and visualizing data from the heavyRAIN API.

## Quick start:

1. Set up this notebooks project with `pip`:
````bash
python -m venv .venv
. .\.venv\Scripts\Activate.ps1 
pip install --upgrade pip
pip install -r requirements.txt
````
or using `uv`: 
````bash
uv sync
````

2. Configure your API connection:
   
- Option A: create a `config/.env` file with following content:
````bash
IOT_API_BASE=<URL>
IOT_API_TOKEN=<your_token_here> 
````

- Option B: hard-code the values directly in `utils/iot_client.py`

3. Run the notebooks inside your IDE

## Repository structure

#### [notebooks/](./notebooks)
Jupyter notebooks for different types of data

#### [utils/](./utils)
Some auxiliary functions

#### [config/](./config)
API and other settings

## Common issues:

- 401/403 errors → check your token in `config/.env` or Swagger UI.
- Connection errors → API server not running
- Empty results → no data for selected city or date range.
- TypeError: no numeric data to plot → handled automatically when converting rain_value.

