import logging
import os
import sys
from src.ops.config import get_config
from src.ops.provisioner import Provisioner


def setup_logging(logfile: str):
    # Pastikan folder log tersedia
    os.makedirs(os.path.dirname(logfile), exist_ok=True)

    # --- Custom StreamHandler untuk aman dari UnicodeEncodeError ---
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                self.stream.write(msg + self.terminator)
                self.flush()
            except UnicodeEncodeError:
                # fallback: encode pakai utf-8 supaya tidak error di Windows
                msg = self.format(record).encode("utf-8", "replace").decode("utf-8")
                self.stream.write(msg + self.terminator)
                self.flush()

    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))

    file_handler = logging.FileHandler(logfile, encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
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
