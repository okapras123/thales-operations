import requests
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class CTVLClient:
    def __init__(self, base_url: str, admin_user: str, admin_pass: str, verify_ssl: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
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
        """Authenticate ke CTVL."""
        url = urljoin(self.base_url + "/", "api/api-token-auth/")
        payload = {"username": self.admin_user, "password": self.admin_pass}
        logger.debug("Authenticating to CTVL %s", url)
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        token = data.get("access") or data.get("token")
        if not token:
            raise RuntimeError("Authentication response contains no token")
        self.token = token
        return token

    def create_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/users/")
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "is_active": True,
            "is_staff": True,
            "is_superuser": False
        }
        logger.debug("Creating CTVL user: %s", username)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_key(self, name: str, seedkey: bool = False) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/keys/")
        payload = {"name": name, "seedkey": seedkey}
        logger.debug("Creating CTVL key: %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        # print(r.text)
        r.raise_for_status()
        return r.json()

    def grant_permission_token(self, user: str, key: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/permissions/token/users/")
        payload = {"user": user, "key": key, "asymkey": None, "opaqueobj": None, "canPost": True, "canGet": True}
        logger.debug("Granting token permission to %s for key %s", user, key)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def grant_permission_crypto(self, user: str, key: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/permissions/crypto/users/")
        payload = {"user": user, "key": key, "asymkey": None, "opaqueobj": None, "canDecrypt": True, "canEncrypt": False, "canSign": False, "canVerify": False}
        logger.debug("Granting crypto permission to %s for key %s", user, key)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_token_group(self, name: str, key: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/tokengroups/")
        payload = {"name": name, "key": key}
        logger.debug("Creating token group %s", name)
        r = requests.post(url, json=payload, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_token_template(self, body: Dict[str, Any]) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", "api/tokentemplates/")
        logger.debug("Creating token template %s", body.get("name"))
        r = requests.post(url, json=body, headers=self._headers(), verify=self.verify_ssl, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
