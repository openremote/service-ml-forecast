from pydantic import BaseModel
import tomli
from pathlib import Path

class AppInfo (BaseModel):
    name: str
    description: str
    version: str

def get_app_info() -> AppInfo | None:
    """Read app info (name, description, version) from pyproject.toml file."""
    try:
        pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
        
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
           
        return AppInfo(**pyproject_data["project"])
    except (FileNotFoundError, KeyError, tomli.TOMLDecodeError) as e:
        return None

__app_info__ = get_app_info()


