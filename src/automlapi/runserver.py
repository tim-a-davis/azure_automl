"""Entry point for running the FastAPI application with Uvicorn."""

import uvicorn

from automlapi.main import app


def main():
    """Launch the FastAPI app using Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
