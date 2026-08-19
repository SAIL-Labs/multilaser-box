"""
Airtable Sync for Lantern Test Reports

Talks to the SAIL "Lantern Manufacture" Airtable base:

- list_device_serials() queries the Devices table so the GUI can offer
  known lantern serials (UUID field = "PL-{serial}") instead of relying
  on typed input.
- push_report() upserts one Throughput Tests record plus one Port
  Measurements record per port, mirroring the "Ingest Lantern Test
  Report" Office Script: raw powers only are written (IL and %
  throughput are live Airtable formulas), while median IL, port std
  (ddof=1) and worst port number are computed here. Upserts are keyed
  on Report Filename / Measurement ID, so pushing the same report again
  is safe.

Requires a personal access token (PAT) scoped to data.records:read/write
on this base. Uses only the standard library (urllib), like updater.py.

Author: Multi-Laser Box Project
Date: 2026-08-20
"""

from __future__ import annotations

import json
import logging
import math
import re
import ssl
import statistics
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

API_URL = "https://api.airtable.com/v0"

BASE_ID = "appFohM47HRWATP9a"
TESTS_TABLE = "tblhV0LtUE5cymzXv"
PORTS_TABLE = "tblEklJLKOVtZUqvf"
DEVICES_TABLE = "tblYJVYm0gs8lpaSN"

DEVICE_UUID_PREFIX = "PL-"
# Devices in these lifecycle states can't be tested, so the pairing list
# skips them (a blank Status still passes the filter)
EXCLUDED_DEVICE_STATUSES = ("Raw", "Disposed", "No Fibre")

# Throughput Tests field IDs
TEST_FIELDS = {
    "testId": "fldTfFmEMKcuYZuvs",
    "reportFilename": "fldTwTLQyP3Slkoqm",
    "device": "fldzuuXnj6UJ8OBPr",
    "testDate": "fld0Aq3it8FMHVRBy",
    "method": "flde0mqu85rE5QoxJ",
    "wavelength": "fldZapHjEjydo4Q3l",
    "launch": "fldc9TMoualsMpHRt",
    "pmref": "fldgV5NMmpFJmRw7n",
    "medianIl": "fldvrAolKezkE2LVM",
    "portStd": "fldxs371jnWy6PoEA",
    "worstPort": "fldFG0ks7sBYXNeoe",
}
# Port Measurements field IDs
PORT_FIELDS = {
    "measurementId": "fld1xzYI6QrLDNJwS",
    "test": "fldIHeRjABvJ4LOuX",
    "port": "fldyyIqh4uUQmKzIN",
    "thruMw": "fldP5BvR6xCDIn9Ok",
    "refUw": "fldyxJLUCA6wAugKn",
}

UPSERT_BATCH_SIZE = 10  # Airtable's per-request record limit


def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context, falling back to certifi if system certs fail."""
    ctx = ssl.create_default_context()
    try:
        if ctx.get_ca_certs():
            return ctx
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    return ssl.create_default_context()


_ssl_context = _create_ssl_context()


class AirtableSyncError(Exception):
    """Exception raised for Airtable sync errors.

    The `status` attribute holds the HTTP status code when the error came
    from an Airtable response (e.g. 401/403 for a bad or underscoped PAT),
    or None for network-level failures.
    """

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def _request(
    pat: str,
    method: str,
    path: str,
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: float = 15.0,
) -> dict:
    """Perform one Airtable API request and return the decoded JSON"""
    url = f"{API_URL}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(
            req, timeout=timeout, context=_ssl_context
        ) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        if e.code in (401, 403):
            message = (
                "Airtable rejected the access token (check that the PAT is "
                "valid and scoped to data.records:read/write on the Lantern "
                f"Manufacture base).\n\nDetails: {detail}"
            )
        else:
            message = f"Airtable request failed ({e.code}): {detail}"
        raise AirtableSyncError(message, status=e.code)
    except urllib.error.URLError as e:
        raise AirtableSyncError(f"Could not reach Airtable: {e.reason}")
    except (TimeoutError, OSError) as e:
        raise AirtableSyncError(f"Could not reach Airtable: {e}")


def _list_records(pat: str, table_id: str, params: dict) -> List[dict]:
    """Fetch all records from a table, following pagination offsets"""
    records: List[dict] = []
    offset = None
    while True:
        page_params = dict(params)
        if offset:
            page_params["offset"] = offset
        data = _request(pat, "GET", f"{BASE_ID}/{table_id}", params=page_params)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            return records


def _escape_formula_string(value: str) -> str:
    """Escape a string for use inside single quotes in filterByFormula"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def list_device_serials(pat: str) -> List[str]:
    """Return known lantern serials from the Devices table.

    Serials are the UUID field values with the "PL-" prefix stripped
    (UUID "PL-250712-01" -> serial "250712-01", matching what goes in the
    report's B1 cell). Sorted newest-first (serials start with YYMMDD).
    """
    # Filter and sort server-side: fetching only PL- devices in a
    # testable status keeps the page count (one sequential round-trip
    # per 100 records) down
    prefix = _escape_formula_string(DEVICE_UUID_PREFIX)
    conditions = [
        f"LEFT({{UUID}}, {len(DEVICE_UUID_PREFIX)}) = '{prefix}'"
    ] + [
        f"{{Status}} != '{_escape_formula_string(status)}'"
        for status in EXCLUDED_DEVICE_STATUSES
    ]
    records = _list_records(
        pat,
        DEVICES_TABLE,
        {
            "fields[]": "UUID",
            "pageSize": 100,
            "filterByFormula": "AND(" + ", ".join(conditions) + ")",
            "sort[0][field]": "UUID",
            "sort[0][direction]": "desc",
        },
    )
    serials = []
    for rec in records:
        uuid = str(rec.get("fields", {}).get("UUID", "") or "").strip()
        if uuid.startswith(DEVICE_UUID_PREFIX):
            serials.append(uuid[len(DEVICE_UUID_PREFIX):])
    serials.sort(reverse=True)
    logger.info(f"Fetched {len(serials)} device serial(s) from Airtable")
    return serials


def push_report(
    pat: str,
    filename: str,
    serial: str,
    wavelength_nm: Optional[float],
    pmref_uw: float,
    launch_mw: float,
    ports: Sequence[Tuple[int, float, float]],
) -> Dict:
    """Upsert one test report into Airtable.

    Args:
        filename: Report filename, the Throughput Tests upsert key.
        serial: Lantern serial (report B1); Device link uses UUID
            "PL-{serial}" and Measurement IDs "{serial}-P{port:02d}".
        wavelength_nm: Test wavelength.
        pmref_uw: PMREF reference reading (uW, report B17).
        launch_mw: Launch power (mW, report B18).
        ports: (port_number, throughput_mW, reference_uW) per measured port.

    Returns:
        Summary dict: created (bool), test_id (str or None for updates),
        device_linked (bool), n_ports, mean_il_db, worst_port.
    """
    serial = (serial or "").strip()
    if not serial:
        raise AirtableSyncError("The report has no lantern serial number (cell B1)")
    if not ports:
        raise AirtableSyncError("The report has no measured ports to push")
    if not (pmref_uw and pmref_uw > 0 and launch_mw and launch_mw > 0):
        raise AirtableSyncError(
            "PMREF and Launch must be recorded (use Calibrate Now) before pushing"
        )

    # ---- Stats (mirror the Office Script / ingest_test_report.py) ----
    cal = launch_mw / pmref_uw
    ils = []
    for port, thru_mw, ref_uw in ports:
        if thru_mw <= 0 or ref_uw <= 0:
            raise AirtableSyncError(
                f"Port {port} has a non-positive power value; "
                "cannot compute insertion loss"
            )
        ils.append(10.0 * math.log10(thru_mw / (cal * ref_uw)))
    median_il = statistics.median(ils)
    port_std = statistics.stdev(ils) if len(ils) > 1 else None
    mean_il = sum(ils) / len(ils)
    worst_port = ports[ils.index(min(ils))][0]

    date_match = re.match(r"^(\d{2})(\d{2})(\d{2})-", serial)
    test_date = (
        f"20{date_match[1]}-{date_match[2]}-{date_match[3]}" if date_match else None
    )

    # ---- Device lookup by UUID ----
    uuid = _escape_formula_string(f"{DEVICE_UUID_PREFIX}{serial}")
    dev_data = _request(
        pat,
        "GET",
        f"{BASE_ID}/{DEVICES_TABLE}",
        params={"filterByFormula": f"{{UUID}} = '{uuid}'", "maxRecords": 1},
    )
    dev_records = dev_data.get("records", [])
    device_id = dev_records[0]["id"] if dev_records else None
    if device_id is None:
        logger.warning(f"No Device with UUID PL-{serial}; test will be unlinked")

    # ---- Existing test? (decides whether to mint a new TT number) ----
    name = _escape_formula_string(filename)
    ex_data = _request(
        pat,
        "GET",
        f"{BASE_ID}/{TESTS_TABLE}",
        params={
            "filterByFormula": f"{{Report Filename}} = '{name}'",
            "maxRecords": 1,
        },
    )
    existing = bool(ex_data.get("records"))

    new_test_id = None
    if not existing:
        max_n = 0
        for rec in _list_records(
            pat,
            TESTS_TABLE,
            {"fields[]": TEST_FIELDS["testId"], "pageSize": 100},
        ):
            m = re.match(r"^TT-(\d+)$", str(rec.get("fields", {}).get("Test ID", "")))
            if m:
                max_n = max(max_n, int(m[1]))
        new_test_id = f"TT-{max_n + 1:04d}"

    # ---- Upsert the test record ----
    test_fields: Dict[str, object] = {
        TEST_FIELDS["reportFilename"]: filename,
        TEST_FIELDS["testDate"]: test_date,
        TEST_FIELDS["method"]: "PM port sweep",
        TEST_FIELDS["wavelength"]: wavelength_nm,
        TEST_FIELDS["launch"]: launch_mw,
        TEST_FIELDS["pmref"]: pmref_uw,
        TEST_FIELDS["medianIl"]: round(median_il, 6),
        TEST_FIELDS["worstPort"]: worst_port,
    }
    if port_std is not None:
        test_fields[TEST_FIELDS["portStd"]] = round(port_std, 6)
    if device_id:
        test_fields[TEST_FIELDS["device"]] = [device_id]
    if not existing:
        test_fields[TEST_FIELDS["testId"]] = new_test_id

    test_data = _request(
        pat,
        "PATCH",
        f"{BASE_ID}/{TESTS_TABLE}",
        body={
            "performUpsert": {"fieldsToMergeOn": [TEST_FIELDS["reportFilename"]]},
            "records": [{"fields": test_fields}],
            "typecast": True,
        },
    )
    test_rec_id = test_data["records"][0]["id"]

    # ---- Upsert port records in batches ----
    port_records = [
        {
            "fields": {
                PORT_FIELDS["measurementId"]: f"{serial}-P{port:02d}",
                PORT_FIELDS["test"]: [test_rec_id],
                PORT_FIELDS["port"]: port,
                PORT_FIELDS["thruMw"]: thru_mw,
                PORT_FIELDS["refUw"]: ref_uw,
            }
        }
        for port, thru_mw, ref_uw in ports
    ]
    for i in range(0, len(port_records), UPSERT_BATCH_SIZE):
        _request(
            pat,
            "PATCH",
            f"{BASE_ID}/{PORTS_TABLE}",
            body={
                "performUpsert": {
                    "fieldsToMergeOn": [PORT_FIELDS["measurementId"]]
                },
                "records": port_records[i : i + UPSERT_BATCH_SIZE],
                "typecast": True,
            },
        )

    label = "Updated existing test" if existing else f"Created {new_test_id}"
    logger.info(
        f"{label} for {serial}: {len(ports)} ports, "
        f"mean IL {mean_il:.3f} dB, worst P{worst_port:02d}"
        + ("" if device_id else " (no matching Device, left unlinked)")
    )
    return {
        "created": not existing,
        "test_id": new_test_id,
        "device_linked": device_id is not None,
        "n_ports": len(ports),
        "mean_il_db": mean_il,
        "worst_port": worst_port,
    }
