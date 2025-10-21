# src/ops/ctm_client.py
import requests
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class CTMClient:
    def __init__(self, base_url: str, admin_user: str, admin_pass: str, verify_ssl: bool = True, timeout: int = 30):
        self.base_url = base_url
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def authenticate(self) -> str:
        url = urljoin(self.base_url + "/", "api/v1/auth/tokens/")
        payload = {
            "grant_type": "password",
            "username": self.admin_user,
            "password": self.admin_pass
        }
        logger.debug("Authenticating to CTM %s", url)
        r = requests.post(url, json=payload, headers={"accept":"application/json","Content-Type":"application/json"}, verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        jwt = data.get("jwt") or data.get("access_token") or data.get("token")
        if not jwt:
            raise RuntimeError("Authentication response contains no JWT/token")
        self.token = jwt
        return jwt

    def create_user(self, username: str, password: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/usermgmt/users")
        payload = {
            "app_metadata": {},
            "email": email,
            "name": name or username,
            "username": username,
            "password": password,
            "user_metadata": {}
        }
        logger.debug("Creating user %s", username)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_key(self, name: str, owner_id: str, algorithm: str = "AES", size: int = 256, aliases: Optional[list] = None, usageMask: int = 3145740) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/v1/vault/keys2")
        aliases = aliases or [{"alias": name, "type": "string"}]
        
        payload = {
            "name": name,
            "usageMask": usageMask,
            "algorithm": algorithm,
            "size": size,
            "meta": {"ownerId": owner_id, "permissions": {}},
            "aliases": aliases,
            "unexportable": False,
            "undeletable": False
        }
        logger.debug("Creating key %s for owner %s", name, owner_id)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
