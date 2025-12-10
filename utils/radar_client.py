from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from minio import Minio

from config.loader import get_settings


@dataclass
class RadarMetadata:
    """Simple container for one radar metadata row returned by /radar."""
    file_name: str
    sensing_start: datetime
    sensing_end: datetime
    region: str


class RadarClient:
    """
    Helper for:
    - calling the /radar API (DB → file_name inside bucket)
    - downloading .scu files from MinIO.
    """

    def __init__(
        self,
        api_base_url: str = "http://localhost:8030/heavyrain/data-api/api",
        api_token: Optional[str] = None,
    ) -> None:
        # Load shared settings (MinIO + radar paths)
        self.settings = get_settings()

        if self.settings.radar is None:
            raise RuntimeError(
                "settings.radar is None – please check that your dev.yaml "
                "contains a 'radar:' section and that your .env points to it."
            )

        # --- API config ---
        self.api_base_url = api_base_url.rstrip("/")
        # plaintext token for RBAC – same as Swagger “Authorize”
        self.api_token = api_token or ""

        # --- MinIO client ---
        self._minio = Minio(**self.settings.radar.client.model_dump())

        # All radar products share the same bucket ("heavyrain")
        self._bucket = self.settings.radar.file_paths.nrw_q1.bucket_name

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

    def list_radar_metadata(
        self,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        *,
        hours: int = 168,
        region: Optional[str] = None,   # "NRW" or "LfU"
        quality: Optional[str] = None,  # "Q1" or "Q3"
        limit: int = 1000,
        offset: int = 0,
        order: str = "desc",
    ) -> List[RadarMetadata]:
        """
        Call GET /radar and return a list of RadarMetadata objects.
        Mirrors the FastAPI endpoint in your API.
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
            params["region"] = region

        if quality is not None:
            params["quality"] = quality

        url = f"{self.api_base_url}/radar"

        resp = requests.get(url, params=params, headers=self._headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        out: List[RadarMetadata] = []
        for row in data:
            out.append(
                RadarMetadata(
                    file_name=row["file_name"],
                    sensing_start=datetime.fromisoformat(row["sensing_start"]),
                    sensing_end=datetime.fromisoformat(row["sensing_end"]),
                    region=row["region"],
                )
            )
        return out

    # ---------- public API: MinIO download by file_name from DB ----------

    def download_objects(
        self,
        file_names: Iterable[str],
        destination_dir: Path,
    ) -> List[Path]:
        """
        Download the given object paths from MinIO into destination_dir.
        'file_names' are taken directly from sat_radar.hr_radar_data.file_name.
        """
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        paths: List[Path] = []
        for loc in file_names:
            object_name = loc.lstrip("/")  # MinIO needs a relative key
            filename = Path(object_name).name
            dest_path = dest_dir / filename

            self._minio.fget_object(
                bucket_name=self._bucket,
                object_name=object_name,
                file_path=str(dest_path),
            )
            paths.append(dest_path)

        return paths

    # ---------- public API: MinIO download by datetime + region + quality ----------

    def _resolve_target_root(self, region: str, quality: str) -> str:
        """
        Map (region, quality) → radar.file_paths.*.target
        """
        region = region.upper()
        quality = quality.upper()

        if region == "NRW" and quality == "Q1":
            return self.settings.radar.file_paths.nrw_q1.target.rstrip("/")
        if region == "NRW" and quality == "Q3":
            return self.settings.radar.file_paths.nrw_q3.target.rstrip("/")
        if region in {"LFU", "LFU_Q3"} and quality == "Q3":
            return self.settings.radar.file_paths.lfu_q3.target.rstrip("/")

        raise ValueError(f"Unsupported combination region={region!r}, quality={quality!r}")

    def build_prefix_for_datetime(self, region: str, quality: str, ts: datetime) -> str:
        """
        Build MinIO prefix based on
        radar/<REGION_Q#>/<YYMMDD>/hd*.scu

        Example:
        radar/NRW_Q1/250901/
        """
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_utc = ts.astimezone(timezone.utc)

        date_folder = ts_utc.strftime("%y%m%d")  # e.g. 250901
        root = self._resolve_target_root(region, quality)
        return f"{root}/{date_folder}/"

    def list_objects_for_datetime(self, region: str, quality: str, ts: datetime):
        """
        List all MinIO objects under the generated prefix for a given date.
        """
        prefix = self.build_prefix_for_datetime(region, quality, ts)
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
        quality: str,
        ts: datetime,
        destination_dir: Path,
    ) -> List[Path]:
        """
        Download all radar objects for the given region + quality + date.
        (Jira cell #2 requirement.)
        """
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        objs = self.list_objects_for_datetime(region, quality, ts)
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
