"""Standalone ASGI entrypoint for the Veris backend.

Reflex deployment mounts the same app through ``rx.App(api_transformer=api)``.
This file mirrors the working TrueID-BE pattern and gives us a direct Uvicorn
entrypoint for local checks or any host that expects ``main:app``.
"""

from veris.api.routes import api as app


def main() -> None:
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
