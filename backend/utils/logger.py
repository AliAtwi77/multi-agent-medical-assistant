from loguru import logger
import sys
from backend.config.settings import LOG_LEVEL

logger.remove()
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"  # <--- Fixed: added '>'
)

logger.add(
    "./data/app.log",
    level="DEBUG",
    rotation="7 days",
    backtrace= True,
    diagnose= False,
)

__all__ = ["logger"]