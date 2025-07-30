"""Small utility helpers not tied to LangChain."""

import getpass
import os


def load_environ_vars() -> None:
    """Set basic environment variables needed for a run."""
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = getpass.getpass(
            "Enter API key for Google Gemini: "
        )
