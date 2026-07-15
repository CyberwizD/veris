"""Reflex app shell and backend API mount for Veris."""

import reflex as rx

from veris.api.routes import api


class State(rx.State):
    """Minimal app state for the Reflex shell."""


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.heading("Veris", size="8"),
                rx.badge("DCP KPI trust layer", variant="soft"),
                justify="between",
                width="100%",
            ),
            rx.text(
                "Reflex-hosted API backend for synthetic KPI generation, validation rules, "
                "and Data Quality Score reporting."
            ),
            rx.code("/api/health"),
            rx.code("/api/demo?records=750&seed=42"),
            rx.code("/api/validate"),
            spacing="4",
            align="start",
            padding_y="3rem",
        ),
        max_width="960px",
    )


app = rx.App(api_transformer=api)
app.add_page(index)
