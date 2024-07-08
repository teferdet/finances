import logging
import sys

log_file_path = "files/program.log"

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', 
                    handlers=[
                        logging.FileHandler(log_file_path, mode='w'),
                        logging.StreamHandler(sys.stdout)
                    ])

logger = logging.getLogger()
