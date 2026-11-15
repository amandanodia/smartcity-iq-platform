import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import HTTPRedirectHandler
from abc import ABC, abstractmethod
from io import BytesIO, StringIO
from urllib.parse import urlparse

import pandas as pd

logger = logging.getLogger(__name__)


class ConnectorError(RuntimeError):
    """A provider request failed or its resource needs configuration."""


class ConnectorNotConfigured(ConnectorError):
    pass


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts):
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        host_ok = parsed.hostname and any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in self.allowed_hosts)
        if parsed.scheme != "https" or not host_ok or parsed.port not in (None, 443):
            raise ConnectorError("Provider attempted to redirect outside its approved HTTPS domain.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class BaseConnector(ABC):
    source_name = ""

    @abstractmethod
    def fetch(self, **options):
        """Fetch source data. Implementations must not normalize source values."""


class JsonApiConnector(BaseConnector):
    allowed_hosts = frozenset()

    def _request(self, url, headers=None, params=None, data=None, method=None, max_bytes=25 * 1024 * 1024):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.port not in (None, 443) or not any(
            parsed.hostname == host or parsed.hostname.endswith("." + host) for host in self.allowed_hosts
        ):
            raise ConnectorError("Provider URL must use HTTPS on an approved provider domain.")
        if params:
            separator = "&" if parsed.query else "?"
            url = url + separator + urllib.parse.urlencode(params, doseq=True)
        request = urllib.request.Request(url, data=data, headers={"Accept": "application/json", "User-Agent": "SmartCityIQ/0.1"} | (headers or {}), method=method)
        try:
            opener = urllib.request.build_opener(_SafeRedirectHandler(self.allowed_hosts))
            with opener.open(request, timeout=20) as response:
                payload = response.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            logger.warning("Provider request failed: source=%s status=%s", self.source_name, exc.code)
            raise ConnectorError(f"Provider returned HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("Provider request failed: source=%s error=%s", self.source_name, type(exc).__name__)
            raise ConnectorError("Provider request failed or timed out.") from exc
        if len(payload) > max_bytes:
            raise ConnectorError("Provider response exceeded the configured response-size limit.")
        logger.info("Provider response received: source=%s bytes=%s", self.source_name, len(payload))
        return payload

    def _json(self, url, headers=None, params=None):
        payload = self._request(url, headers=headers, params=params)
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError("Provider response was not valid JSON.") from exc


class DataGovConnector(JsonApiConnector):
    """data.gov.in resource API. Resource IDs and keys come from configuration."""
    source_name = "data.gov.in"
    allowed_hosts = frozenset({"api.data.gov.in"})
    base_url = "https://api.data.gov.in/resource/"

    def fetch(self, resource_id=None, limit=100, offset=0, **filters):
        api_key = os.getenv("DATA_GOV_IN_API_KEY")
        if not api_key:
            raise ConnectorNotConfigured("Set DATA_GOV_IN_API_KEY to use the data.gov.in resource API.")
        if not resource_id or not str(resource_id).strip():
            raise ConnectorNotConfigured("Configure the verified data.gov.in resource ID for this dataset.")
        limit = min(max(int(limit), 1), 1000)
        params = {"api-key": api_key, "format": "json", "limit": limit, "offset": max(0, int(offset))}
        params.update({f"filters[{key}]": value for key, value in filters.items() if value is not None})
        return self._json(self.base_url + urllib.parse.quote(str(resource_id), safe=""), params=params)


class OpenAqConnector(JsonApiConnector):
    source_name = "OpenAQ"
    allowed_hosts = frozenset({"api.openaq.org"})
    base_url = "https://api.openaq.org/v3/"

    def fetch(self, endpoint="locations", **params):
        api_key = os.getenv("OPENAQ_API_KEY")
        if not api_key:
            raise ConnectorNotConfigured("Set OPENAQ_API_KEY for OpenAQ API v3 requests.")
        endpoint = endpoint.strip("/")
        if not endpoint or ".." in endpoint or endpoint.startswith("http"):
            raise ConnectorError("OpenAQ endpoint must be a relative API v3 path.")
        params["limit"] = min(max(int(params.get("limit", 100)), 1), 1000)
        return self._json(self.base_url + endpoint, headers={"X-API-Key": api_key}, params=params)


class ResourceFileConnector(JsonApiConnector):
    """Fetch an explicitly registered resource URL from one provider domain."""
    allowed_hosts = frozenset()

    def fetch(self, resource_url=None, **_options):
        if not resource_url:
            raise ConnectorNotConfigured("Set a verified downloadable resource_url in this dataset's connector configuration.")
        payload = self._request(resource_url, headers={"Accept": "text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/json"})
        path = urlparse(resource_url).path.lower()
        if path.endswith(".csv"):
            return pd.read_csv(StringIO(payload.decode("utf-8-sig")), dtype=object, keep_default_na=False).to_dict(orient="records")
        if path.endswith((".xlsx", ".xls")):
            return pd.read_excel(BytesIO(payload), dtype=object, keep_default_na=False).to_dict(orient="records")
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError("Resource must be a CSV, Excel workbook, or JSON file with a matching extension.") from exc


class SmartCitiesConnector(ResourceFileConnector):
    source_name = "Smart Cities Mission Data Portal"
    allowed_hosts = frozenset({"smartcities.data.gov.in"})


class CpcbConnector(ResourceFileConnector):
    source_name = "CPCB"
    allowed_hosts = frozenset({"cpcb.nic.in", "cpcbccr.com"})


class CensusConnector(ResourceFileConnector):
    source_name = "Census of India"
    allowed_hosts = frozenset({"censusindia.gov.in"})


class OpenCityConnector(ResourceFileConnector):
    source_name = "OpenCity / MoRTH resource"
    allowed_hosts = frozenset({"data.opencity.in"})


class OpenStreetMapConnector(JsonApiConnector):
    """Uses Overpass only when a specific query and approved endpoint are configured."""
    source_name = "OpenStreetMap"
    allowed_hosts = frozenset({"overpass-api.de", "overpass.kumi.systems"})

    def fetch(self, endpoint="https://overpass-api.de/api/interpreter", query=None, **_options):
        if not query:
            raise ConnectorNotConfigured("Configure an Overpass query for the requested map features.")
        payload = self._request(endpoint, headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                                data=urllib.parse.urlencode({"data": query}).encode("utf-8"), method="POST",
                                max_bytes=25 * 1024 * 1024)
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConnectorError("Overpass response was not valid JSON.") from exc


class CgwbConnector(ResourceFileConnector):
    source_name = "Central Ground Water Board"
    allowed_hosts = frozenset({"cgwb.gov.in", "indiawris.gov.in", "indiawris.nrsc.gov.in"})

    def fetch(self, resource_url=None, **options):
        if not resource_url:
            raise ConnectorNotConfigured("CGWB data needs a verified downloadable resource URL; portal coverage alone is not an API configuration.")
        return super().fetch(resource_url=resource_url, **options)


class ManualImportConnector(BaseConnector):
    source_name = "Manual CSV/Excel import"

    def fetch(self, **_options):
        raise ConnectorNotConfigured("This source requires an uploaded CSV or Excel file.")


_CONNECTORS = {
    "smartcities": SmartCitiesConnector,
    "smart cities mission data portal": SmartCitiesConnector,
    "data.gov.in": DataGovConnector,
    "datagovin": DataGovConnector,
    "open government data platform india": DataGovConnector,
    "cpcb": CpcbConnector,
    "central pollution control board": CpcbConnector,
    "openaq": OpenAqConnector,
    "census": CensusConnector,
    "census of india": CensusConnector,
    "opencity": OpenCityConnector,
    "morth": OpenCityConnector,
    "opencity / morth resource": OpenCityConnector,
    "opencity / morth road accidents": OpenCityConnector,
    "osm": OpenStreetMapConnector,
    "openstreetmap": OpenStreetMapConnector,
    "cgwb": CgwbConnector,
    "central ground water board": CgwbConnector,
    "manual": ManualImportConnector,
}


def get_connector(provider):
    connector_type = _CONNECTORS.get((provider or "").strip().lower())
    if connector_type is None:
        raise ConnectorNotConfigured(f"No connector is registered for provider '{provider}'.")
    return connector_type()
