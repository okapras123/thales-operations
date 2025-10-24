# src/ops/config.py
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env from project root

@dataclass
class AppConfig:
    ctm_host: str
    admin_user: str
    admin_pass: str
    ctvl_host: str
    ctvl_admin_user: str
    ctvl_admin_pass: str
    verify_ssl: bool
    log_file: str
    default_email_domain: str
    timeout_seconds: int
    cte_owner_id: str

def get_config() -> AppConfig:
    ctm_host = os.getenv("CTM_HOST", "https://127.0.0.1")
    admin_user = os.getenv("CTM_ADMIN_USER", "admin")
    admin_pass = os.getenv("CTM_ADMIN_PASS", "password")
    verify_ssl = os.getenv("VERIFY_SSL", "False").lower() in ("1", "true", "yes")
    log_file = os.getenv("LOG_FILE", "log/provision.log")
    default_email_domain = os.getenv("DEFAULT_EMAIL_DOMAIN", "example.local")
    timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "30"))

    ctvl_host = os.getenv("CTVL_HOST", "https://127.0.0.1")
    ctvl_admin_user = os.getenv("CTVL_ADMIN_USER", "admin")
    ctvl_admin_pass = os.getenv("CTVL_ADMIN_PASS", "password")
    cte_owner_id = os.getenv("CTE_OWNER_ID", "local|15feac1d-af25-42e5-893f-854989884d5e")

    return AppConfig(
        ctm_host=ctm_host.rstrip("/"),
        admin_user=admin_user,
        admin_pass=admin_pass,
        ctvl_host=ctvl_host,
        ctvl_admin_user=ctvl_admin_user,
        ctvl_admin_pass=ctvl_admin_pass,
        verify_ssl=verify_ssl,
        log_file=log_file,
        default_email_domain=default_email_domain,
        timeout_seconds=timeout_seconds,
        cte_owner_id=cte_owner_id
    )