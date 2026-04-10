import importlib.metadata
import logging

logger = logging.getLogger(__name__)

def get_package_version(package_name: str = "iwa-rnaseq-reporter") -> str:
    """
    Safely retrieve the installed version of the package.
    Returns "unknown" if the package is not found or an error occurs.
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
    except Exception as e:
        logger.warning(f"Failed to retrieve version for {package_name}: {e}")
        return "unknown"
