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

---

## 📡 Radar & Satellite Data

We now support retrieving radar `.scu` files and satellite imagery from MinIO via the heavyRAIN API.

### 🔧 Setup (required)
Extend your `config/.env` file with:

```bash
RADAR_API_BASE=<URL>
RADAR_API_TOKEN=<token>
MINIO_ENDPOINT=<minio-url>
MINIO_ACCESS_KEY=<your-access-key>
MINIO_SECRET_KEY=<your-secret-key>

### Notebook examples

| Notebook | Data Type | Notes |
|----------|-----------|------|
| `notebooks/radar_data_example.ipynb` | Radar `.scu` via MinIO | Uses RADAR_* config variables |
| `notebooks/satellite_data_example.ipynb` | Satellite imagery via MinIO | Uses MINIO_* and SAT_* variables |

Make sure you have configured your `.env` file before running these notebooks.
