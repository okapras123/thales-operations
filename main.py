# main.py
import logging
import os
from src.ops.config import get_config
from src.ops.provisioner import Provisioner

def setup_logging(logfile: str):
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(logfile),
            logging.StreamHandler()
        ]
    )

def main():
    cfg = get_config()
    setup_logging(cfg.log_file)
    logger = logging.getLogger("main")
    logger.info("Starting provisioning tool")
    excel_path = os.getenv("INPUT_EXCEL", "config/input.xlsx")
    p = Provisioner(excel_path, cfg)
    results = p.run()
    logger.info("Done. Results written to log.")

if __name__ == "__main__":
    main()
