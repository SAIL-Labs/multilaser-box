"""
Measurement Logger
Logs power meter measurements to Excel (.xlsx) or CSV (.csv) files.

Excel logs follow the SAIL lantern-fabrication throughput layout, generated
programmatically: columns A-D hold Trial, Port, injection power and lantern
output power, while prefilled formulas in columns E-G and I-T compute
throughput, loss and per-port statistics. CSV logs store the same data with
throughput and loss computed at log time.

Requirements:
- openpyxl (optional): pip install openpyxl  -- required for Excel logging only

Author: Multi-Laser Box Project
Date: 2026-07-13
"""

import csv
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.worksheet.formula import ArrayFormula

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

CSV_HEADER = [
    "timestamp",
    "trial",
    "port",
    "injection_power_W",
    "lantern_output_power_W",
    "throughput",
    "loss_percent",
    "loss_dB",
    "wavelength_nm",
]

# Throughput worksheet layout constants (1-indexed openpyxl columns)
COL_TRIAL = 1  # A
COL_PORT = 2  # B
COL_INJECTION = 3  # C
COL_OUTPUT = 4  # D
COL_THROUGHPUT = 5  # E
FIRST_DATA_ROW = 2
PREFILLED_ROWS = 415  # rows with throughput/loss formulas prefilled
SUMMARY_PORTS = 7  # per-port statistics rows (I2:O8)

XLSX_HEADERS = {
    "A1": "Trial",
    "B1": "Port",
    "C1": "injection power",
    "D1": "lantern output power",
    "E1": "throughput",
    "F1": "loss %",
    "G1": "loss dB",
    "I1": "Port",
    "J1": "injection power",
    "K1": "lantern output power",
    "L1": "throughput",
    "M1": "throughput std",
    "N1": "loss %",
    "O1": "loss dB",
    "Q1": "Overall Throughput",
    "R1": "Std",
    "S1": "Overall Loss",
    "T1": "Overall Average dB",
}

XLSX_COLUMN_WIDTHS = {
    "C": 24.5,
    "D": 21.2,
    "E": 12.5,
    "F": 11.0,
    "G": 11.0,
    "P": 10.2,
    "Q": 12.0,
}


class MeasurementLogError(Exception):
    """Exception raised for measurement logging errors"""

    pass


class MeasurementLogger:
    """Appends power measurements to an Excel or CSV log file.

    The file format is inferred from the file extension (.xlsx or .csv).
    The file is opened, written and closed on every append so it is safe
    to inspect between measurements (but must not be open in Excel while
    logging).
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        suffix = self.file_path.suffix.lower()

        if suffix == ".xlsx":
            if not OPENPYXL_AVAILABLE:
                raise MeasurementLogError(
                    "Excel logging requires the openpyxl package.\n"
                    "Install it with: pip install openpyxl\n"
                    "Alternatively, use a .csv log file."
                )
            self.format = "xlsx"
        elif suffix == ".csv":
            self.format = "csv"
        else:
            raise MeasurementLogError(
                f"Unsupported log file type: '{suffix}' (use .xlsx or .csv)"
            )

    def create_new(self, wavelength_nm: Optional[int] = None):
        """Create a new log file, overwriting any existing file.

        Excel logs are generated with the throughput worksheet layout on a
        sheet named 'wave_<wavelength>'. CSV logs are created with a header
        row.
        """
        if self.format == "xlsx":
            self._create_xlsx(wavelength_nm)
        else:
            self._create_csv()
        logger.info(f"Created measurement log: {self.file_path}")

    def append_measurement(
        self,
        port: int,
        injection_power_w: Optional[float],
        output_power_w: Optional[float],
        wavelength_nm: Optional[int] = None,
    ) -> int:
        """Append one measurement row and return its trial number."""
        if self.format == "xlsx":
            return self._append_xlsx(port, injection_power_w, output_power_w)
        return self._append_csv(port, injection_power_w, output_power_w, wavelength_nm)

    # === Excel implementation ===

    def _create_xlsx(self, wavelength_nm: Optional[int]):
        wb = openpyxl.Workbook()
        # openpyxl writes no cached formula results; make Excel recalculate
        wb.calculation.fullCalcOnLoad = True
        ws = wb.active
        ws.title = f"wave_{wavelength_nm}" if wavelength_nm else "throughput"

        header_font = Font(bold=True)
        for coord, header in XLSX_HEADERS.items():
            ws[coord] = header
            ws[coord].font = header_font
        for column, width in XLSX_COLUMN_WIDTHS.items():
            ws.column_dimensions[column].width = width

        # Per-measurement throughput/loss formulas (columns E-G)
        for row in range(FIRST_DATA_ROW, PREFILLED_ROWS + 1):
            self._write_row_formulas(ws, row)

        # Per-port statistics (columns I-O): the port list spills from a
        # UNIQUE/FILTER formula; _xlfn/_xlws prefixes are how openpyxl must
        # write post-2007 Excel function names
        last = FIRST_DATA_ROW + SUMMARY_PORTS - 1
        ws["I2"] = ArrayFormula(
            f"I2:I{last}",
            '=_xlfn.UNIQUE(_xlfn._xlws.FILTER(B:B, (B:B<>"") * (B:B<>"Port")))',
        )
        for row in range(FIRST_DATA_ROW, last + 1):
            for col, src in (("J", "C"), ("K", "D"), ("L", "E"), ("N", "F"), ("O", "G")):
                ws[f"{col}{row}"] = (
                    f'=IFERROR(AVERAGEIF($B:$B,$I{row},{src}:{src}),"")'
                )
            ws[f"M{row}"] = ArrayFormula(
                f"M{row}",
                f'=IFERROR(_xlfn.STDEV.S(_xlfn._xlws.FILTER(E:E,B:B=$I{row})),"")',
            )
            for col, fmt in (("L", "0.0%"), ("M", "0.0%"), ("N", "0.0%")):
                ws[f"{col}{row}"].number_format = fmt

        # Overall statistics (columns Q-T)
        ws["Q2"] = f"=AVERAGE(L2:L{last})"
        ws["R2"] = f"=_xlfn.STDEV.S(L2:L{last})"
        ws["S2"] = f"=AVERAGE(N2:N{last})"
        ws["T2"] = f"=AVERAGE(O2:O{last})"
        for coord, fmt in (("Q2", "0.0%"), ("R2", "0.0%"), ("S2", "0.0%"), ("T2", "0.00")):
            ws[coord].number_format = fmt

        try:
            wb.save(self.file_path)
        except PermissionError:
            raise MeasurementLogError(self._locked_file_message())
        except OSError as e:
            raise MeasurementLogError(f"Failed to create log file:\n{str(e)}")

    @staticmethod
    def _write_row_formulas(ws, row: int):
        """Write the throughput/loss %/loss dB formulas for one data row"""
        ws[f"E{row}"] = f'=IFERROR(D{row}/C{row},"")'
        ws[f"F{row}"] = f'=IFERROR(1-E{row},"")'
        ws[f"G{row}"] = f'=IFERROR(10*LOG10(E{row}),"")'
        ws[f"E{row}"].number_format = "0.0%"
        ws[f"F{row}"].number_format = "0.0%"
        ws[f"G{row}"].number_format = "0.00"

    def _append_xlsx(
        self,
        port: int,
        injection_power_w: Optional[float],
        output_power_w: Optional[float],
    ) -> int:
        if not self.file_path.exists():
            raise MeasurementLogError(f"Log file not found: {self.file_path}")
        try:
            wb = openpyxl.load_workbook(self.file_path)
        except PermissionError:
            raise MeasurementLogError(self._locked_file_message())
        except Exception as e:
            raise MeasurementLogError(f"Failed to open log file:\n{str(e)}")

        ws = wb.worksheets[0]

        # Find the last row containing data in columns A-D and the highest
        # trial number so far (tolerates blank spacer rows in the template)
        last_data_row = FIRST_DATA_ROW - 1
        last_trial = 0
        for row in ws.iter_rows(
            min_row=FIRST_DATA_ROW, min_col=COL_TRIAL, max_col=COL_OUTPUT
        ):
            if any(cell.value is not None for cell in row):
                last_data_row = row[0].row
            trial_value = row[0].value
            if isinstance(trial_value, (int, float)):
                last_trial = max(last_trial, int(trial_value))

        next_row = last_data_row + 1
        trial = last_trial + 1

        ws.cell(row=next_row, column=COL_TRIAL, value=trial)
        ws.cell(row=next_row, column=COL_PORT, value=port)
        if injection_power_w is not None:
            ws.cell(row=next_row, column=COL_INJECTION, value=injection_power_w)
        if output_power_w is not None:
            ws.cell(row=next_row, column=COL_OUTPUT, value=output_power_w)

        # Extend throughput/loss formulas if beyond the prefilled rows
        if ws.cell(row=next_row, column=COL_THROUGHPUT).value is None:
            self._write_row_formulas(ws, next_row)

        try:
            wb.save(self.file_path)
        except PermissionError:
            raise MeasurementLogError(self._locked_file_message())
        except OSError as e:
            raise MeasurementLogError(f"Failed to save log file:\n{str(e)}")

        logger.info(
            f"Logged trial {trial} (port {port}) to {self.file_path.name}"
        )
        return trial

    # === CSV implementation ===

    def _create_csv(self):
        try:
            with open(self.file_path, "w", newline="") as f:
                csv.writer(f).writerow(CSV_HEADER)
        except (PermissionError, OSError) as e:
            raise MeasurementLogError(f"Failed to create log file:\n{str(e)}")

    def _append_csv(
        self,
        port: int,
        injection_power_w: Optional[float],
        output_power_w: Optional[float],
        wavelength_nm: Optional[int],
    ) -> int:
        # Determine the next trial number from existing rows
        last_trial = 0
        needs_header = True
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", newline="") as f:
                    for row in csv.reader(f):
                        if not row:
                            continue
                        needs_header = False
                        try:
                            last_trial = max(last_trial, int(row[1]))
                        except (IndexError, ValueError):
                            pass  # header or malformed row
            except OSError as e:
                raise MeasurementLogError(f"Failed to read log file:\n{str(e)}")

        trial = last_trial + 1

        throughput = loss_percent = loss_db = None
        if (
            injection_power_w is not None
            and output_power_w is not None
            and injection_power_w > 0
        ):
            throughput = output_power_w / injection_power_w
            loss_percent = (1.0 - throughput) * 100.0
            if throughput > 0:
                loss_db = 10.0 * math.log10(throughput)

        def fmt(value, spec="{:.6e}"):
            return spec.format(value) if value is not None else ""

        try:
            with open(self.file_path, "a", newline="") as f:
                writer = csv.writer(f)
                if needs_header:
                    writer.writerow(CSV_HEADER)
                writer.writerow(
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        trial,
                        port,
                        fmt(injection_power_w),
                        fmt(output_power_w),
                        fmt(throughput, "{:.6f}"),
                        fmt(loss_percent, "{:.4f}"),
                        fmt(loss_db, "{:.4f}"),
                        wavelength_nm if wavelength_nm is not None else "",
                    ]
                )
        except (PermissionError, OSError) as e:
            raise MeasurementLogError(f"Failed to write log file:\n{str(e)}")

        logger.info(
            f"Logged trial {trial} (port {port}) to {self.file_path.name}"
        )
        return trial

    def _locked_file_message(self) -> str:
        return (
            f"Cannot write to '{self.file_path.name}'.\n"
            "The file is probably open in Excel — close it and try again."
        )
