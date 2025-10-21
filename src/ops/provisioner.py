# src/ops/provisioner.py
import logging
from .ctm_client import CTMClient
from .excel_reader import ExcelReader
from .config import AppConfig, get_config
from .ctvl_client import CTVLClient
from typing import Tuple
import secrets, string
import time

logger = logging.getLogger(__name__)

def random_username(prefix: str, max_len: int = 20) -> str:
    base = prefix.lower().replace(" ", "")
    # add suffix random letters/digits
    name = f"{base}_apps"
    return name[:max_len]

def random_password(prefix: str = "", length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    # ensure at least one lower, upper, digit, symbol
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*()-_=+" for c in pwd)):
            return (prefix + pwd)[:64]

class Provisioner:
    def __init__(self, excel_path: str, cfg: AppConfig):
        self.excel = ExcelReader(excel_path)
        self.cfg = cfg
        self.client = CTMClient(
            cfg.ctm_host, cfg.admin_user, cfg.admin_pass,
            verify_ssl=cfg.verify_ssl, timeout=cfg.timeout_seconds
        )
        self.ctvl = CTVLClient(
            cfg.ctvl_host, cfg.ctvl_admin_user, cfg.ctvl_admin_pass,
            verify_ssl=cfg.verify_ssl, timeout=cfg.timeout_seconds
        )

    def _create_templates_for_charset(self, app_name: str, charset: str):
        name_base = app_name.lower().replace(" ", "")
        charset = charset.strip().lower()

        templates = []

        if charset == "clear":
            templates.append({
                "name": f"{name_base}_templateclear",
                "format": "FPE",
                "keepleft": 100,
                "keepright": 0,
                "irreversible": True,
                "copyruntdata": True,
                "allowsmallinput": True,
                "charset": "Alphanumeric",
                "prefix": "",
                "startyear": 0,
                "endyear": 0
            })
        elif charset == "alphanumeric":
            templates.append({
                "name": f"{name_base}_template",
                "format": "FPE",
                "keepleft": 0,
                "keepright": 0,
                "irreversible": False,
                "copyruntdata": False,
                "allowsmallinput": True,
                "charset": "Alphanumeric",
                "prefix": "",
                "startyear": 0,
                "endyear": 0
            })
        elif charset == "digit":
            templates.append({
                "name": f"{name_base}_templatedigit",
                "format": "FPE",
                "keepleft": 0,
                "keepright": 0,
                "irreversible": False,
                "copyruntdata": False,
                "allowsmallinput": True,
                "charset": "All digits",
                "prefix": "",
                "startyear": 0,
                "endyear": 0
            })

        return templates


    def run(self):
        settings = self.excel.read_settings()
        workshops = settings.get("Workshops API", {}).get("status", False)
        if not workshops:
            logger.info("Workshops API disabled in settings. Nothing to do.")
            return

        df_workshops = self.excel.read_workshops_api()
        # authenticate once (with retry)
        # Auth ke CTM
        for attempt in range(3):
            try:
                token = self.client.authenticate()
                logger.info("Authenticated to CTM, token len=%d", len(token))
                break
            except Exception as e:
                logger.warning("Auth failed (attempt %d): %s", attempt+1, e)
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise
        # Auth ke CTVL
        for attempt in range(3):
            try:
                self.ctvl.authenticate()
                break
            except Exception as e:
                logger.warning("CTVL Auth failed (%d): %s", attempt+1, e)
                time.sleep(2)

        results = []
        for _, row in df_workshops.iterrows():
            raw_app_name = str(row.get("Apps Name", "")).strip()
            app_name = raw_app_name.lower().replace(" ", "")
            charset = str(row.get("Character Set", "")).strip()
            charset_list = [c.strip() for c in charset.split(",") if c.strip()]
            if not app_name:
                logger.warning("Skipping row with empty Apps Name")
                continue

            # generate credentials
            username = random_username(app_name)
            password = random_password(prefix=app_name.lower())
            email_domain = self.cfg.default_email_domain
            email_local = app_name.lower().replace(" ", "")  # basic
            email = f"{email_local}@{email_domain}"
            tg_name = f"{app_name}_tgroup"

            logger.info("Provisioning app=%s user=%s email=%s", app_name, username, email)

            # ========== STEP 1–3: CTM PROVISIONING (AS IS) ==========
            try:
                user_resp = self.client.create_user(username=username, password=password, email=email, name=app_name)
            except Exception as e:
                logger.exception("Failed to create user for %s: %s", app_name, e)
                results.append({"app": app_name, "status": "user_failed", "error": str(e)})
                continue

            owner_id = user_resp.get("user_id") or user_resp.get("id") or user_resp.get("userId")
            if not owner_id:
                owner_id = user_resp.get("data", {}).get("user_id") if isinstance(user_resp.get("data"), dict) else None

            if not owner_id:
                logger.error("Could not find owner id in create_user response: %s", user_resp)
                results.append({"app": app_name, "status": "user_no_ownerid", "response": user_resp})
                continue

            key_name = f"{app_name.lower().replace(' ','')}_keys"
            try:
                key_resp = self.client.create_key(name=key_name, owner_id=owner_id)
            except Exception as e:
                logger.exception("Failed to create key for %s: %s", app_name, e)
                results.append({"app": app_name, "status": "key_failed", "error": str(e), "owner_id": owner_id})
                continue

            # ========== STEP 4–6: CTVL PROVISIONING (dengan validasi & fallback) ==========
            try:
                logger.info("Starting CTVL provisioning for %s", app_name)

                # --- STEP 4: Create user on CTVL ---
                ctvl_user_resp = self.ctvl.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                # --- STEP 5: Create key on CTVL (reuse from CTM) ---
                ctvl_key_resp = self.ctvl.create_key(name=key_name)

                # --- STEP 6: Grant permissions (use key_name, not key_id) ---
                try:
                    perm_token = self.ctvl.grant_permission_token(user=username, key=key_name)
                    perm_crypto = self.ctvl.grant_permission_crypto(user=username, key=key_name)
                except Exception as e:
                    logger.exception("CTVL: Failed to grant permissions for %s: %s", app_name, e)
                    results.append({
                        "app": app_name,
                        "status": "ctvl_permission_failed",
                        "error": str(e),
                        "ctvl_user_response": ctvl_user_resp,
                        "ctvl_key_response": ctvl_key_resp
                    })
                    continue

                # 7. Create token group (once per app)
                tg_resp = self.ctvl.create_token_group(name=tg_name, key=key_name)

                # 8. Create token templates per charset
                tpl_results = []
                for cset in charset_list:
                    tpl_defs = self._create_templates_for_charset(app_name, cset)
                    for tpl in tpl_defs:
                        tpl["tenant"] = tg_name  # set tenant ke tokengroup
                        resp = self.ctvl.create_token_template(tpl)
                        tpl_results.append(resp)

                # ✅ success
                results.append({
                    "app": raw_app_name,
                    "status": "ok",
                    "username": username,
                    "password": password,
                    "email": email,
                    "user_response": user_resp,
                    "key_response": key_resp,
                    "ctvl_user_response": ctvl_user_resp,
                    "ctvl_key_response": ctvl_key_resp,
                    "ctvl_perm_token": perm_token,
                    "ctvl_perm_crypto": perm_crypto,
                    "ctvl_tokengroup": tg_resp,
                    "ctvl_templates": tpl_results,
                })

            except Exception as e:
                logger.exception("CTVL: Unexpected error provisioning %s: %s", raw_app_name, e)
                results.append({"app": raw_app_name, "status": "ctvl_failed", "error": str(e)})
                continue

        summary_lines = []
        for r in results:
            if r.get("status") == "ok":
                tpls = [tpl.get("name") for tpl in r.get("ctvl_templates", [])]
                summary_lines.append(
                    f"\nApp: {r['app']}\n"
                    f"  Username : {r['username']}\n"
                    f"  Password : {r['password']}\n"
                    f"  Email    : {r['email']}\n"
                    f"  Tenant   : {r['ctvl_tokengroup'].get('name')}\n"
                    f"  Templates: {', '.join(tpls)}\n"
                )

        if summary_lines:
            logger.info("=== Provisioning Summary ===%s", "".join(summary_lines))
        else:
            logger.info("No successful provisioning to summarize.")

        logger.info("Provisioning finished. Summary: %s", summary_lines)
        return results
