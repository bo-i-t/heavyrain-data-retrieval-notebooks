# config/schemas.py
from __future__ import annotations
from typing import List, Optional, Tuple, Literal, Iterable
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus
import ssl
import os


Role = Literal["reader", "writer"]


class DBConnSettings(BaseModel):
    drivername: str = "postgresql+asyncpg"
    host: str
    port: int = 5432
    username: str
    password: Optional[str] = None
    database: str

    def build_sqlalchemy_url(self, host: Optional[str] = None, port: Optional[int] = None) -> str:
        h = host or self.host
        p = port or self.port
        user = quote_plus(self.username)
        pwd = f":{quote_plus(self.password)}" if self.password else ""
        return f"{self.drivername}://{user}{pwd}@{h}:{p}/{self.database}"


class SSLSettings(BaseModel):
    sslmode: str = "verify-full"
    sslcert: Optional[str] = None
    sslrootcert: Optional[str] = None
    sslkey: Optional[str] = None

    def build_asyncpg_ssl(self) -> Optional[ssl.SSLContext]:
        mode = (self.sslmode or "").lower()

        if mode in {"disable", "allow", "prefer"}:
            return None

        cafile = self._expand(self.sslrootcert)
        ctx = ssl.create_default_context(cafile=cafile if cafile else None)

        certfile = self._expand(self.sslcert)
        keyfile = self._expand(self.sslkey)
        if certfile and keyfile:
            ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)

        if mode in {"verify-full", "verify_ca", "verify-ca"}:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True
        else:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True

        return ctx

    @staticmethod
    def _expand(p: Optional[str]) -> Optional[str]:
        if not p:
            return p
        return os.path.abspath(os.path.expanduser(p))

    def as_connect_args(self) -> dict:
        d = {"sslmode": self.sslmode}
        if self.sslcert:
            d["sslcert"] = self.sslcert
        if self.sslrootcert:
            d["sslrootcert"] = self.sslrootcert
        if self.sslkey:
            d["sslkey"] = self.sslkey
        return d


class SSHSettings(BaseModel):
    ssh_address_or_host: Tuple[str, int]
    ssh_username: str
    ssh_pkey: Optional[str] = None
    remote_bind_address: Tuple[str, int]
    local_bind_address: Tuple[str, int]


class DBSettings(BaseModel):
    db_settings: DBConnSettings
    ssl_settings: Optional[SSLSettings] = None
    ssh_settings: Optional[SSHSettings] = None


class MinioClient(BaseSettings):
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool = True


# ---- Radar -----------------------------------------------------------------

class RadarProductFilePath(BaseSettings):
    source: str
    target: str
    bucket_name: str


class FilePath(BaseSettings):
    nrw_q1: RadarProductFilePath
    nrw_q3: RadarProductFilePath
    nrw_q3_storage: RadarProductFilePath
    lfu_q3: RadarProductFilePath


class RadarDataSettings(BaseSettings):
    client: MinioClient
    file_paths: FilePath


# ---- Satellite -------------------------------------------------------------
class SatelliteApiSettings(BaseSettings):
    endpoint: str
    consumer_key: str = ""
    consumer_secret: str = ""
    pi: str



class SatelliteProductFilePath(BaseSettings):
    source: str
    target: str
    bucket_name: str


class SatelliteFilePaths(BaseSettings):
    raw: SatelliteProductFilePath


class SatelliteDataSettings(BaseSettings):
    api: SatelliteApiSettings
    client: MinioClient
    file_paths: SatelliteFilePaths
    minutes: int


class Settings(BaseSettings):
    env: str = Field(default="dev", validation_alias="APP_ENV")

    db: Optional[DBSettings] = None
    radar: Optional[RadarDataSettings] = None
    sat: Optional[SatelliteDataSettings] = None

    sqlalchemy_echo: bool = False
    sqlalchemy_pool_size: int = 10
    sqlalchemy_max_overflow: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _prod_hardening(self):
        if self.env == "prod":
            pass
        return self
