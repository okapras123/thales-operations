# 🛡️ Thales CipherTrust Data Security Automation Toolkit

An automation toolkit for **Thales CipherTrust Data Security Platform**  
Built with ❤️ in Python to simplify and standardize the setup of **CipherTrust modules** — including:

- 🔐 CipherTrust Transparent Encryption (CTE)
- 🧩 VaultLink (CTVL)
- 🧰 Workshop API provisioning
- ⚙️ Key, Profile, and Token management

---

## 🚀 Overview

This toolkit automates the provisioning and configuration workflows for Thales CipherTrust products.  
It can automatically create **encryption keys**, **client profiles**, and **registration tokens**, all driven by configuration files (Excel + `.env`).

Designed for:
- Rapid environment setup  
- Consistent provisioning  
- Large-scale enterprise integration  

---

## 🧩 Project Structure
```bash
operations/
│
├── src/
│ ├── ops/
│ │ ├── cte/
│ │ │ └── cte_provisioner.py
│ │ ├── excel_reader.py
│ │ ├── provisioner.py
│ │ ├── config.py
│ │ └── ctm_client.py
│ └── ...
│
├── Configs/
│ └── sample_configs.xlsx # Example Excel configuration
│
├── .env # Environment variables file
├── env.sample # Sample env template
├── requirements.txt
├── main.py # Entry point
└── README.md
```

---

## ⚙️ Setup & Deployment

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-org>/<repo-name>.git
cd <repo-name>
2️⃣ Create and Activate Virtual Environment
```
```python
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# or
.venv\Scripts\activate         # Windows
```
```python
3️⃣ Install Dependencies

pip install -r requirements.txt
```

4️⃣ Prepare Configurations

a. Create the Configs folder
```bash
mkdir Configs
cp sample_configs.xlsx Configs/
b. Copy the environment file

cp env.sample .env
```

Then open .env and adjust to match your CipherTrust Manager settings.

🧠 Environment Variables (.env)
Example .env file:

```bash
# CipherTrust Manager Settings
CTM_HOST=https://XXX.XXX.XXX.XXX
CTM_ADMIN_USER=admin
CTM_ADMIN_PASS=yourpassword

# CipherTrust VaultLink (optional)
CTVL_HOST=https://XXX.XXX.XXX.XXX
CTVL_ADMIN_USER=admin
CTVL_ADMIN_PASS=yourpassword

# Logging and Behavior
LOG_FILE=log/provision.log
VERIFY_SSL=False
TIMEOUT_SECONDS=30
DEFAULT_EMAIL_DOMAIN=example.local
```

▶️ Run the Provisioning

After setup, simply run:

python main.py
The tool will automatically:

Authenticate to CipherTrust Manager (CTM)

Read client data from Excel

Create CTE Keys, Client Profiles, and Registration Tokens

Log all actions to console and file (log/provision.log)

📜 Example Log Output
```yaml
2025-10-24 15:10:29,876 INFO src.ops.cte.cte_provisioner - [CTE] Starting CTE Provisioning process
2025-10-24 15:10:31,421 INFO src.ops.cte.cte_provisioner - [CTE] Created CTE key: ldt_myapp_keys
2025-10-24 15:10:31,670 INFO src.ops.cte.cte_provisioner - [CTE] Created registration token for myapp | token: ZZZZZZ
2025-10-24 15:10:33,109 INFO src.ops.cte.cte_provisioner - ✅ Successfully provisioned CTE client: myapp
```

📊 Excel Configuration Format
The Excel file defines the list of applications/clients to be provisioned.
Example columns:

Application Name	Max Allowed	Description
mytesla	5	Tesla CTE Client
mybank	10	Bank Data Encryption Client

The tool will automatically use the following naming conventions:

Key Name: ldt_<app_name>_keys

Profile Name: <app_name>_client

Alias: <app_name>_client

🧰 Development Notes
UTF-8 safe logging (no emoji crash on Windows)

.env controls SSL and timeout behavior

Easy to extend for other CipherTrust modules (CTVL, DSM, etc.)

Each provisioning step fully logged for traceability

👨‍💻 Author & Credits
Developed by NERA Engineering Team
Project: Telkom Data Protection – Thales CipherTrust Automation
Maintained by: Oka Prasetiyo

Made with ❤️ for better, faster, and safer data security integration.

📄 License
This project is proprietary and confidential.
Unauthorized copying, modification, or redistribution is strictly prohibited.