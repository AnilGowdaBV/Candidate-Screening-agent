"""Application configuration loaded from environment and .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_SEARCH_URL = (
    "https://www.instahyre.com/employer/search/results/?"
    "boolean_query=%28+GO+OR+Golang+AND+Routines+AND+%28+LLD+OR+HLD+OR+%22System+Design%22+"
    "OR+%22Distributed+Systems%22+OR+SOLID+%29+AND+%28+Leetcode+OR+codechef+OR+hackerrank+"
    "OR+Scaler+OR+Crio+OR+%22Coding+ninjas%22+OR+ICPC+OR+codeforces+OR+Geeksforgeeks+%29+%29"
    "&company_size=50%2C200%2C500%2C1000&entire_resume=true&gender=1"
    "&hide_viewed_by_others=false&hide_viewed_by_self=false&job_functions=1%3A10"
    "&large_company_size=true&limit_count=true&management_role=1&mid_company_size=true"
    "&must_match_education=false&notice_period=0&pg_education=0&salary_max=10&salary_min=4"
    "&search_skill_option=1&selected_search_option=3&small_company_size=false&status=1"
    "&ug_education=0&workex_max=3&workex_min=1"
)


class Settings(BaseSettings):
    """Strongly typed application settings."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development", description="App environment")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    # Instahyre Credentials
    INSTAHYRE_EMAIL: Optional[str] = Field(default=None, description="Instahyre account email")
    INSTAHYRE_PASSWORD: Optional[SecretStr] = Field(default=None, description="Instahyre account password")
    INSTAHYRE_SEARCH_URL: Optional[str] = Field(
        default=DEFAULT_SEARCH_URL,
        description="Search results URL (provided by user for each screening run)",
    )

    @field_validator("INSTAHYRE_SEARCH_URL", mode="before")
    @classmethod
    def default_search_url_if_empty(cls, v):
        if not v or (isinstance(v, str) and not v.strip()):
            return DEFAULT_SEARCH_URL
        return v

    # GitHub Credentials
    GITHUB_TOKEN: Optional[SecretStr] = Field(
        default=None, description="Official GitHub REST API token"
    )
    GITHUB_TOKEN_PART1: Optional[str] = Field(default=None)
    GITHUB_TOKEN_PART2: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def resolve_token(self):
        if not self.GITHUB_TOKEN and self.GITHUB_TOKEN_PART1 and self.GITHUB_TOKEN_PART2:
            self.GITHUB_TOKEN = SecretStr(
                f"{self.GITHUB_TOKEN_PART1.strip()}{self.GITHUB_TOKEN_PART2.strip()}"
            )
        return self

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/screening_agent.db",
        description="Local SQLite database connection string",
    )

    # Operational Options
    DRY_RUN: bool = Field(
        default=True,
        description="When true, proposed notes are logged but not submitted to Instahyre",
    )
    HEADLESS_BROWSER: bool = Field(
        default=False,
        description="Whether to run the Playwright browser without visible window",
    )
    MAX_CANDIDATES_PER_RUN: int = Field(
        default=500,
        description="Maximum candidates to inspect per screening run",
    )
    API_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=15,
        description="Network request timeout in seconds",
    )

    @property
    def is_github_token_configured(self) -> bool:
        """Check if a non-empty GitHub token is configured."""
        if self.GITHUB_TOKEN and self.GITHUB_TOKEN.get_secret_value().strip():
            return True
        return False

    @property
    def is_instahyre_configured(self) -> bool:
        """Check if Instahyre email and password are provided."""
        has_email = bool(self.INSTAHYRE_EMAIL and self.INSTAHYRE_EMAIL.strip())
        has_password = bool(
            self.INSTAHYRE_PASSWORD and self.INSTAHYRE_PASSWORD.get_secret_value().strip()
        )
        return has_email and has_password

    def get_safe_status(self) -> dict:
        """Return safe configuration status with zero secrets."""
        return {
            "environment": self.ENVIRONMENT,
            "log_level": self.LOG_LEVEL,
            "dry_run": self.DRY_RUN,
            "headless_browser": self.HEADLESS_BROWSER,
            "max_candidates_per_run": self.MAX_CANDIDATES_PER_RUN,
            "instahyre_search_url": self.INSTAHYRE_SEARCH_URL,
            "is_github_configured": self.is_github_token_configured,
            "is_instahyre_configured": self.is_instahyre_configured,
            "database_url": self.DATABASE_URL,
        }


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
