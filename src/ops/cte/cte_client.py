# src/ops/cte/cte_client.py
import requests
import logging
from urllib.parse import urljoin
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class CTEClient:
    def __init__(self, base_url: str, token: str, verify_ssl: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        }

    def create_key(self, name: str, owner_id: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/vault/keys2")
        payload = {
            "name": name,
            "usageMask": 12,
            "algorithm": "AES",
            "size": 256,
            "meta": {
                "cte": {
                    "is_used": True,
                    "cte_versioned": True,
                    "encryption_mode": "CBC",
                    "unique_to_client": False,
                    "persistent_on_client": True
                }
            },
            "ownerId": owner_id,
            "permissions": {
                "ReadKey": ["CTE Clients"],
                "ExportKey": ["CTE Clients"]
            },
            "aliases": [{"alias": name, "type": "string"}],
            "unexportable": False,
            "undeletable": True
        }

        logger.info("Creating CTE key: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_profile(self, name: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/client-management/profiles/")
        payload = {"name": name}
        logger.info("Creating CTE profile: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_registration_token(self, profile_id: str, max_allowed: int, name_prefix: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/client-management/regtokens")
        payload = {
            "client_management_profile_id": profile_id,
            "lifetime": "10h",
            "max_clients": max_allowed,
            "name_prefix": name_prefix
        }
        logger.info("Creating registration token for profile %s", name_prefix)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_user_set(self, name: str, description: str, users: List[str]) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/transparent-encryption/usersets/")
        payload = {
            "name": name,
            "description": description,
            "users": [{"uname": u.strip()} for u in users if u.strip()]
        }
        logger.info("Creating user set: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_process_set(self, name: str, description: str, process_list: List[str]) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/transparent-encryption/processsets/")
        payload = {
            "name": name,
            "description": description,
            "processes": [{"pname": p.strip()} for p in process_list if p.strip()]
        }
        logger.info("Creating process set: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_policy(self, name: str, user_set_id: str, current_key: str, transformation_key: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/transparent-encryption/policies/")
        payload = {
            "name": name,
            "policy_type": "LDT",
            "never_deny": False,
            "security_rules": [
                {"order_number": 1, "effect": "permit,applykey", "action": "key_op", "partial_match": False, "exclude_resource_set": False},
                {"order_number": 2, "effect": "permit", "action": "f_rd_att,f_rd_sec,d_rd_att,d_rd,d_rd_sec", "partial_match": True, "exclude_resource_set": False},
                {"order_number": 3, "effect": "permit,audit,applykey", "action": "all_ops", "partial_match": True, "user_set_id": user_set_id, "exclude_resource_set": False},
                {"order_number": 4, "effect": "permit,audit", "action": "read", "partial_match": True, "exclude_resource_set": False},
                {"order_number": 5, "effect": "deny,audit", "action": "all_ops", "partial_match": True, "exclude_resource_set": False}
            ],
            "ldt_key_rules": [
                {
                    "current_key": {"key_id": current_key},
                    "is_exclusion_rule": False,
                    "transformation_key": {"key_id": transformation_key}
                }
            ]
        }
        logger.info("Creating policy: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
