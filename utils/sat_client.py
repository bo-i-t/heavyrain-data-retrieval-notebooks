from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from minio import Minio

from config.loader import get_settings


@dataclass
class SatelliteMetadata:
    """Simple container for one satellite metadata row."""
    location: str
    sensing_start: datetime
    sensing_end: datetime


class SatelliteClient:
    """
    Helper for:
    - calling the /satellite API (DB → locations)
    - downloading GeoTIFFs from MinIO.
    """

    def __init__(
        self,
        api_base_url: str = "http://localhost:8030/heavyrain/data-api/api",
        api_token: Optional[str] = None,
    ) -> None:
        # Load shared settings (MinIO + paths)
        self.settings = get_settings()

        # --- API config ---
        self.api_base_url = api_base_url.rstrip("/")
        # plaintext token for RBAC – fill in from env or by manual
        self.api_token = api_token or ""

        # --- MinIO client ---
        self._minio = Minio(**self.settings.sat.client.model_dump())
        self._bucket = self.settings.sat.file_paths.raw.bucket_name
        self._target_prefix = self.settings.sat.file_paths.raw.target.rstrip("/")

    # ---------- internal helpers ----------

    @property
    def _headers(self) -> dict:
        """
        Use the same auth header as Swagger:
        Authorization: Bearer <token>
        """
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}


    @staticmethod
    def _to_utc_iso(dt: datetime) -> str:
        """Convert datetime → ISO-8601 with Z suffix."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    # ---------- public API: DB / HTTP ----------

    def list_satellite_metadata(
        self,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        *,
        hours: int = 24,
        region: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        order: str = "desc",
    ) -> List[SatelliteMetadata]:
        """
        Call GET /satellite and return a list of SatelliteMetadata objects.
        Mirrors the FastAPI endpoint you showed.
        """
        params: dict = {
            "limit": limit,
            "offset": offset,
            "order": order,
        }

        # Either explicit from/to OR "last N hours"
        if from_ts is not None:
            params["from_ts"] = self._to_utc_iso(from_ts)
        if to_ts is not None:
            params["to_ts"] = self._to_utc_iso(to_ts)
        if from_ts is None and to_ts is None:
            params["hours"] = hours

        if region is not None:
            # must be "NRW" or "BOO"
            params["region"] = region

        url = f"{self.api_base_url}/satellite"

        resp = requests.get(url, params=params, headers=self._headers, timeout=60)

        resp.raise_for_status()
        data = resp.json()

        out: List[SatelliteMetadata] = []
        for row in data:
            out.append(
                SatelliteMetadata(
                    location=row["location"],
                    sensing_start=datetime.fromisoformat(row["sensing_start"]),
                    sensing_end=datetime.fromisoformat(row["sensing_end"]),
                )
            )
        return out

    # ---------- public API: MinIO download by location ----------

    def download_objects(
        self,
        locations: Iterable[str],
        destination_dir: Path,
    ) -> List[Path]:
        """
        Download the given object "location" paths from MinIO into destination_dir.
        'locations' are taken directly from hr_satellite_data.location.
        """
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        paths: List[Path] = []
        for loc in locations:
            object_name = loc.lstrip("/")          # safety – MinIO needs relative key
            filename = Path(object_name).name
            dest_path = dest_dir / filename

            self._minio.fget_object(
                bucket_name=self._bucket,
                object_name=object_name,
                file_path=str(dest_path),
            )
            paths.append(dest_path)

        return paths

    # ---------- public API: MinIO download by datetime + region ----------

    def build_prefix_for_datetime(self, region: str, ts: datetime) -> str:
        """
        Build MinIO prefix based on
        satellite/<REGION>/<YYYY>/<MonthName>/<dd>/

        Example:
        satellite/NRW/2025/December/01/
        """
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_utc = ts.astimezone(timezone.utc)

        yyyy = ts_utc.strftime("%Y")
        month_name = ts_utc.strftime("%B")
        dd = ts_utc.strftime("%d")

        return f"{self._target_prefix}/{region}/{yyyy}/{month_name}/{dd}/"

    def list_objects_for_datetime(self, region: str, ts: datetime):
        """
        List all MinIO objects under the generated prefix for a given date.
        """
        prefix = self.build_prefix_for_datetime(region, ts)
        return list(
            self._minio.list_objects(
                bucket_name=self._bucket,
                prefix=prefix,
                recursive=True,
            )
        )

    def download_by_datetime(
        self,
        region: str,
        ts: datetime,
        destination_dir: Path,
    ) -> List[Path]:
        """
        Download all objects for the given region + date.
        (This corresponds to the “generate path from datetime + region” requirement.)
        """
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        objs = self.list_objects_for_datetime(region, ts)
        result: List[Path] = []

        for obj in objs:
            filename = Path(obj.object_name).name
            dest_path = dest_dir / filename

            self._minio.fget_object(
                bucket_name=self._bucket,
                object_name=obj.object_name,
                file_path=str(dest_path),
            )
            result.append(dest_path)

        return result
