# src/ops/excel_reader.py
import pandas as pd
from typing import Dict, Any, List

class ExcelReader:
    def __init__(self, path: str):
        self.path = path

    def read_settings(self) -> Dict[str, Any]:
        """
        Reads 'settings' sheet with expected columns:
        Task | Status | Function | Descriptions | Input
        Function column contains TRUE/FALSE (linked from checkbox).
        """
        df = pd.read_excel(self.path, sheet_name="settings", engine="openpyxl", header=2)
        df = df.fillna("")

        result = {}
        for _, row in df.iterrows():
            task = str(row.get("Task", "")).strip()
            if not task:
                continue

            # Priority: Function > Status
            func_value = row.get("Function", "")
            status_value = row.get("Status", "")

            # normalize boolean from either Function or Status column
            raw_value = func_value if func_value != "" else status_value
            if isinstance(raw_value, bool):
                enabled = raw_value
            elif isinstance(raw_value, (int, float)):
                enabled = bool(raw_value)
            else:
                val = str(raw_value).strip().lower()
                enabled = val in ("true", "yes", "1", "checked", "enabled", "x")

            result[task] = {
                "status": enabled,
                "descriptions": str(row.get("Descriptions", "")).strip(),
                "input": str(row.get("Input", "")).strip()
            }

        return result

    def read_workshops_api(self) -> pd.DataFrame:
        """
        Reads sheet 'workshops_api' with columns:
        Apps Name | Character Set
        Returns a cleaned pandas DataFrame.
        """
        df = pd.read_excel(self.path, sheet_name="workshops_api", engine="openpyxl")
        return df.fillna("")

    def read_cte_provisioning(self) -> List[Dict[str, Any]]:
        """
        Reads 'cte_provisioning' sheet for CTE automation.
        Expected columns:
        client name | current keys | max allowed | authorized_users | authorized process
        """
        df = pd.read_excel(self.path, sheet_name="cte_provisioning", engine="openpyxl")
        df = df.fillna("")

        results = []
        for _, row in df.iterrows():
            cname = str(row.get("client name", "")).strip()
            if not cname:
                continue

            results.append({
                "client_name": cname,
                "current_keys": str(row.get("current keys", "")).strip(),
                "max_allowed": int(row.get("max allowed", 0)),
                "authorized_users": [u.strip() for u in str(row.get("authorized_users", "")).split(",") if u.strip()],
                "authorized_process": [p.strip() for p in str(row.get("authorized process", "")).split(",") if p.strip()]
            })

        return results