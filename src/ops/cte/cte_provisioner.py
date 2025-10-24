# src/ops/cte/cte_provisioner.py
import logging
import requests
from typing import List, Dict, Any
from urllib.parse import urljoin
from ..excel_reader import ExcelReader
from ..config import AppConfig
from ..ctm_client import CTMClient
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



logger = logging.getLogger(__name__)

class CTEProvisioner:
    def __init__(self, cfg: AppConfig, excel_reader: ExcelReader):
        """
        Handles CTE provisioning automation:
        - Create keys, profiles, registration token
        - Create user/process sets
        - Create LDT policy
        """
        self.cfg = cfg
        self.excel = excel_reader
        self.ctm = CTMClient(
            cfg.ctm_host,
            cfg.admin_user,
            cfg.admin_pass,
            verify_ssl=cfg.verify_ssl,
            timeout=cfg.timeout_seconds
        )

    # === Helper Methods ===
    def _post(self, path: str, payload: dict) -> dict:
        """Unified POST request to CTM API."""
        url = urljoin(self.cfg.ctm_host.rstrip("/") + "/", path.lstrip("/"))
        r = requests.post(
            url,
            json=payload,
            headers=self.ctm._headers(),
            verify=self.cfg.verify_ssl,
            timeout=self.cfg.timeout_seconds
        )
        if not r.ok:
            logger.error("POST %s failed: %s", path, r.text)
            logger.debug("Payload: %s", payload)
        r.raise_for_status()
        return r.json()

    # === Main Runner ===
    def run(self) -> List[Dict[str, Any]]:
        logger.info("[CTE] Starting CTE Provisioning process")
        entries = self.excel.read_cte_provisioning()
        if not entries:
            logger.warning("No CTE provisioning data found in Excel.")
            return []

        # Authenticate once
        logger.info("Authenticating to CTM...")
        self.ctm.authenticate()

        results = []
        for entry in entries:
            cname = entry.get("client_name", "").strip().lower().replace(" ", "")
            if not cname:
                logger.warning("Skipping row without client name.")
                continue

            logger.info("=== Provisioning client: %s ===", cname)
            try:
                # === Step 1–3: Create key, profile, registration token ===
                step1 = self._create_key_profile_token(cname, entry)

                # === Step 4–5: Create user/process sets ===
                policy_elements = self._create_policy_elements(cname, entry)

                # === Step 6: Create Policy (core of step 3 request) ===
                policy = self._create_policy(cname, entry, policy_elements, step1)

                results.append({
                    "client": cname,
                    "status": "ok",
                    "key": step1.get("key"),
                    "profile": step1.get("profile"),
                    "registration_token": step1.get("token"),
                    "user_set": policy_elements.get("user_set"),
                    "process_set": policy_elements.get("process_set"),
                    "policy": policy
                })
                logger.info("✅ Successfully provisioned CTE client: %s", cname)

            except Exception as e:
                logger.exception("❌ Failed to provision client %s: %s", cname, e)
                results.append({"client": cname, "status": "failed", "error": str(e)})

        logger.info("CTE Provisioning finished for %d clients", len(results))
        return results

    # === Step 1–3 ===
    def _create_key_profile_token(self, cname: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create Key, Client Profile, and Registration Token for CTE client."""
        key_name = f"ldt_{cname}_keys"
        profile_name = f"{cname}_client"
        owner_id = self.cfg.cte_owner_id  # ambil dari .env

        # Create key (special version for CTE)
        key_resp = self._create_cte_key(key_name, owner_id)
        logger.info("[CTE] Created CTE key: %s", key_resp.get("name"))

        # Create client profile
        profile_payload = {
            "name": profile_name,
            "description": f"Profile for {cname} client",
            "key": key_name,
        }
        profile_resp = self._post("api/v1/client-management/profiles/", profile_payload)
        profile_id = profile_resp.get("id")

        # Create registration token
        token_payload = {
            "client_management_profile_id": profile_id,
            "lifetime": "10h",
            "max_clients": entry.get("max_allowed", 1),
            "name_prefix": profile_name,
        }
        token_resp = self._post("api/v1/client-management/regtokens", token_payload)
        token_value = token_resp.get("token")
        logger.info("[CTE] Created registration token for %s | token: %s", cname, token_value)

        return {"key": key_resp, "profile": profile_resp, "token": token_resp, "profile_id": profile_id}

  # === Helper: create CTE key ===
    def _create_cte_key(self, key_name: str, owner_id: str) -> dict:
        """Create a CTE-compatible key with proper meta and permissions."""
        payload = {
            "name": key_name,
            "usageMask": 12,
            "algorithm": "AES",
            "size": 256,
            "meta": {
                "cte": {
                    "is_used": True,
                    "cte_versioned": True,
                    "encryption_mode": "CBC",
                    "unique_to_client": False,
                    "persistent_on_client": True,
                    "unique_to_client_format": ""
                },
                "ownerId": owner_id,
                "permissions": {
                    "ReadKey": ["CTE Clients"],
                    "ExportKey": ["CTE Clients"]
                }
            },
            "aliases": [
                {"alias": key_name, "type": "string"}
            ],
            "unexportable": False,
            "undeletable": True
        }

        logger.debug("Creating CTE Key with payload: %s", payload)
        return self._post("api/v1/vault/keys2", payload)

    # === Step 4–5 ===
    def _create_policy_elements(self, cname: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        # User set
        user_set_name = f"{cname}_authorized_users"
        user_payload = {
            "name": user_set_name,
            "description": f"Authorized users for app {cname}",
            "users": [{"uname": u} for u in entry.get("authorized_users", []) if u],
        }
        user_resp = self._post("api/v1/transparent-encryption/usersets/", user_payload)

        # Process set (optional)
        proc_resp = None
        if entry.get("authorized_process"):
            proc_set_name = f"{cname}_authorized_process"
            proc_payload = {
                "name": proc_set_name,
                "description": f"Authorized process for app {cname}",
                "processes": [{"pname": p} for p in entry["authorized_process"] if p],
            }
            proc_resp = self._post("api/v1/transparent-encryption/processsets/", proc_payload)

        return {"user_set": user_resp, "process_set": proc_resp}

    # === Step 6 ===
    def _create_policy(
        self,
        cname: str,
        entry: Dict[str, Any],
        policy_elements: Dict[str, Any],
        step1: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implements Step 3 from your spec: Create LDT Policy."""
        policy_name = f"{cname}_Database"
        user_set_id = policy_elements["user_set"].get("name") or policy_elements["user_set"].get("id")
        current_key = entry.get("current_keys")
        transformation_key = f"ldt_{cname}_keys"

        policy_payload = {
            "name": policy_name,
            "policy_type": "LDT",
            "never_deny": False,
            "security_rules": [
                {"order_number": 1, "effect": "permit,applykey", "action": "key_op", "partial_match": False},
                {"order_number": 2, "effect": "permit", "action": "f_rd_att,f_rd_sec,d_rd_att,d_rd,d_rd_sec", "partial_match": True},
                {
                    "order_number": 3,
                    "effect": "permit,audit,applykey",
                    "action": "all_ops",
                    "partial_match": True,
                    "user_set_id": user_set_id,
                },
                {"order_number": 4, "effect": "permit,audit", "action": "read", "partial_match": True},
                {"order_number": 5, "effect": "deny,audit", "action": "all_ops", "partial_match": True},
            ],
            "ldt_key_rules": [
                {
                    "current_key": {"key_id": current_key},
                    "is_exclusion_rule": False,
                    "transformation_key": {"key_id": transformation_key},
                }
            ],
        }

        logger.debug("Creating policy for %s with payload: %s", cname, policy_payload)
        return self._post("api/v1/transparent-encryption/policies/", policy_payload)
