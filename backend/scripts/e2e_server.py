"""The API as the end-to-end tests see it (spec: delivery-pipeline, design D2).

Prepares a fresh `pawdesk_e2e` database seeded as of the demo day, switches the model
client to replay recorded responses (or record them with PAWDESK_E2E_RECORD=1), and
serves the API on port 8011. Started by Playwright's webServer; never used for real work.
"""

import os
from pathlib import Path

import uvicorn

from app.config import get_settings
from app.demo import DEMO_TODAY
from scripts.lab_database import database_url, prepare

E2E_DATABASE = "pawdesk_e2e"
PORT = int(os.environ.get("PAWDESK_E2E_API_PORT", "8011"))
CASSETTES = Path(__file__).resolve().parents[1] / "tests" / "cassettes" / "e2e"


def main() -> None:
    url = database_url(get_settings().database_url, E2E_DATABASE)
    prepare(url, DEMO_TODAY)

    # Environment variables win over .env, so the app's settings pick these up.
    os.environ["DATABASE_URL"] = url
    os.environ["LLM_CASSETTE_DIR"] = str(CASSETTES)
    os.environ["LLM_CASSETTE_MODE"] = (
        "record" if os.environ.get("PAWDESK_E2E_RECORD") == "1" else "replay"
    )
    get_settings.cache_clear()

    print(
        f"e2e API on :{PORT}, database {E2E_DATABASE}, cassettes {os.environ['LLM_CASSETTE_MODE']}"
    )
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
