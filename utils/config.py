from typing import Any, Dict, List, Optional, Union

from pydantic.v1 import SecretStr, BaseSettings
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Settings(BaseSettings):
    PATH_DB :SecretStr
    class Config:
        case_sensitive = True
        env_file = "../.env"


config = Settings()

