"""Strava Analytics Dashboard using Reflex."""

import reflex as rx
from typing import List, Dict
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import StravaDataLoader


class State(rx.State):
    """Application state."""

    # Data
    activities_data: pd.DataFrame = pd.DataFrame()
    activities_list: List[Dict] = []
    weekly_data: pd.DataFrame = pd.DataFrame()

    # Stats
    kms_this_week: float = 0.0
    kms_ytd: float = 0.0
    avg_pace_this_week: float = 0.0

    # UI state
    selected_period: str = "90d"
    loading: bool = True

    # Chart data - prepared for Reflex charts
    weekly_chart_data: List[Dict] = []

    # Formatted pace for display
    formatted_avg_pace: str = "0:00"

    # Activity popup state
    show_activity_popup: bool = False
    selected_activity_name: str = ""
    selected_activity_distance: str = ""
    selected_activity_pace: str = ""

    def load_data(self):
        """Load Strava data from Kedro outputs."""
        try:
            loader = StravaDataLoader()
            df = loader.load_activities()

            if df is not None:
                # Get stats
                stats = loader.get_weekly_stats(df)
                self.kms_this_week = stats["kms_this_week"]
                self.kms_ytd = stats["kms_ytd"]
                self.avg_pace_this_week = stats["avg_pace_this_week"]
                self.formatted_avg_pace = self.format_pace(stats["avg_pace_this_week"])

                # Get weekly data
                self.weekly_data = loader.get_weekly_summary(df, self.selected_period)

                # Get activities list
                self.activities_data = loader.get_activities_list(df)
                # Convert to list of dicts for custom table
                self.activities_list = self.activities_data.to_dict('records')

                # Prepare chart data
                self.prepare_chart_data()

            self.loading = False

        except Exception as e:
            print(f"Error loading data: {e}")
            self.loading = False

    def update_period(self, period: str):
        """Update the selected time period for charts."""
        self.selected_period = period
        self.load_data()

    def format_pace(self, pace_decimal: float) -> str:
        """Convert decimal pace to minute:second format."""
        minutes = int(pace_decimal)
        seconds = int((pace_decimal - minutes) * 60)
        return f"{minutes}:{seconds:02d}"

    def prepare_chart_data(self):
        """Prepare data for Reflex charts."""
        if self.weekly_data.empty:
            self.weekly_chart_data = []
            return

        # Convert pandas DataFrame to list of dicts for Reflex charts
        chart_data = []
        for _, row in self.weekly_data.iterrows():
            chart_data.append({
                "week": row["week"],
                "total_kms": round(float(row["total_kms"]), 1),
                "avg_pace": round(float(row["avg_pace"]), 2),
                "avg_pace_formatted": self.format_pace(float(row["avg_pace"])),
                "total_hours": round(float(row["total_hours"]), 1)
            })

        self.weekly_chart_data = chart_data

    def show_activity_details(self, name: str, distance: str, pace: str):
        """Show activity details in popup."""
        self.selected_activity_name = name
        self.selected_activity_distance = distance
        self.selected_activity_pace = self.format_pace(float(pace))
        self.show_activity_popup = True

    def close_activity_popup(self):
        """Close activity details popup."""
        self.show_activity_popup = False


def stat_card(title: str, value: str, subtitle: str = "") -> rx.Component:
    """Create a statistic card component."""
    return rx.card(
        rx.vstack(
            rx.heading(title, size="4", color="gray.600"),
            rx.heading(value, size="7", color="gray.900", weight="bold"),
            rx.text(subtitle, size="2", color="gray.500"),
            spacing="1",
            align="center"
        ),
        size="3",
        width="100%",
        background="white",
        border="1px solid #e5e7eb"
    )


def period_selector() -> rx.Component:
    """Create period selector buttons."""
    return rx.hstack(
        rx.button(
            "90 Days",
            on_click=State.update_period("90d"),
            variant=rx.cond(State.selected_period == "90d", "solid", "soft"),
            color_scheme="blue"
        ),
        rx.button(
            "6 Months",
            on_click=State.update_period("6m"),
            variant=rx.cond(State.selected_period == "6m", "solid", "soft"),
            color_scheme="blue"
        ),
        rx.button(
            "YTD",
            on_click=State.update_period("ytd"),
            variant=rx.cond(State.selected_period == "ytd", "solid", "soft"),
            color_scheme="blue"
        ),
        rx.button(
            "All Time",
            on_click=State.update_period("all"),
            variant=rx.cond(State.selected_period == "all", "solid", "soft"),
            color_scheme="blue"
        ),
        spacing="2"
    )


def activity_row(name: str, distance: str, time: str, pace: str, date: str) -> rx.Component:
    """Create a single activity row."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(name, weight="bold", size="4", color="gray.900"),
                rx.text(date, size="2", color="gray.500"),
                spacing="1",
                align="start"
            ),
            rx.spacer(),
            rx.hstack(
                rx.vstack(
                    rx.text("Distance", size="1", color="gray.500"),
                    rx.text(f"{distance} km", weight="medium", color="gray.800"),
                    spacing="1",
                    align="center"
                ),
                rx.vstack(
                    rx.text("Time", size="1", color="gray.500"),
                    rx.text(f"{time} min", weight="medium", color="gray.800"),
                    spacing="1",
                    align="center"
                ),
                rx.vstack(
                    rx.text("Pace", size="1", color="gray.500"),
                    rx.text(f"{pace} min/km", weight="medium", color="gray.800"),
                    spacing="1",
                    align="center"
                ),
                spacing="6"
            ),
            justify="between",
            align="center",
            width="100%"
        ),
        size="2",
        width="100%",
        padding="4"
    )


def activities_list() -> rx.Component:
    """Create modern activities list."""
    return rx.card(
        rx.vstack(
            rx.heading("Recent Activities", size="5", color="gray.900"),
            rx.text("Click on any activity to view details", size="2", color="gray.600", style={"font_style": "italic"}),
            rx.cond(
                State.activities_list,
                rx.vstack(
                    rx.foreach(
                        State.activities_list[:20],
                        lambda activity: rx.card(
                            rx.hstack(
                                rx.vstack(
                                    rx.text(activity.name, font_weight="bold", size="4", color="gray.900"),
                                    rx.text(activity.date, size="2", color="gray.500"),
                                    spacing="1",
                                    align="start"
                                ),
                                rx.spacer(),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("Distance", size="1", color="gray.500"),
                                        rx.text(activity.distance_km + " km", weight="medium", color="gray.800"),
                                        spacing="1",
                                        align="center"
                                    ),
                                    rx.vstack(
                                        rx.text("Time", size="1", color="gray.500"),
                                        rx.text(activity.time_minutes + " min", weight="medium", color="gray.800"),
                                        spacing="1",
                                        align="center"
                                    ),
                                    rx.vstack(
                                        rx.text("Pace", size="1", color="gray.500"),
                                        rx.text(activity.pace + " min/km", weight="medium", color="gray.800"),
                                        spacing="1",
                                        align="center"
                                    ),
                                    spacing="6"
                                ),
                                justify="between",
                                align="center",
                                width="100%"
                            ),
                            on_click=State.show_activity_details(activity.name, activity.distance_km, activity.pace),
                            size="2",
                            width="100%",
                            padding="4",
                            style={
                                "cursor": "pointer",
                                "transition": "all 0.2s ease",
                                "_hover": {"transform": "translateY(-2px)", "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)"}
                            }
                        )
                    ),
                    spacing="3",
                    width="100%"
                ),
                rx.text("No activities found", color="gray.500")
            ),
            spacing="4",
            width="100%"
        ),
        size="3",
        width="100%"
    )


def dashboard() -> rx.Component:
    """Main dashboard layout."""
    return rx.container(
        rx.vstack(
            # Header
            rx.heading("🏃 Strava Running Analytics", size="8", color="gray.900", margin_bottom="6"),

            # Statistics Cards
            rx.grid(
                stat_card(
                    "This Week",
                    f"{State.kms_this_week} km",
                    "Total distance"
                ),
                stat_card(
                    "Year to Date",
                    f"{State.kms_ytd} km",
                    "Total distance"
                ),
                stat_card(
                    "Avg Pace This Week",
                    f"{State.formatted_avg_pace} min/km",
                    "Average pace"
                ),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="8"
            ),

            # Period Selector
            rx.hstack(
                rx.text("Time Period:", weight="bold", color="gray.700"),
                period_selector(),
                justify="start",
                align="center",
                margin_bottom="6"
            ),

            # Weekly Distance Chart (Full Width)
            rx.card(
                rx.vstack(
                    rx.heading("Weekly Running Distance", size="4", color="gray.900"),
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="total_kms",
                            stroke="#2563eb",
                            stroke_width=3,
                            type_="monotone"
                        ),
                        rx.recharts.x_axis(data_key="week", interval=0),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        data=State.weekly_chart_data,
                        width="100%",
                        height=400
                    ),
                    spacing="4"
                ),
                size="3",
                width="100%",
                margin_bottom="8"
            ),

            # Side by Side Charts
            rx.grid(
                # Pace Chart
                rx.card(
                    rx.vstack(
                        rx.heading("Average Pace", size="4", color="gray.900"),
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="avg_pace",
                                fill="#059669",
                                stroke="#047857",
                                stroke_width=2,
                                radius=[4, 4, 0, 0]
                            ),
                            rx.recharts.x_axis(data_key="week"),
                            rx.recharts.y_axis(),
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                            rx.recharts.tooltip(
                                cursor={"fill": "transparent"},
                                formatter=[("avg_pace_formatted", "Pace")]
                            ),
                            data=State.weekly_chart_data,
                            width="100%",
                            height=350,
                            margin={"top": 20, "right": 20, "bottom": 20, "left": 20}
                        ),
                        spacing="4",
                        width="100%"
                    ),
                    size="3",
                    width="100%"
                ),
                # Time Chart
                rx.card(
                    rx.vstack(
                        rx.heading("Time Spent", size="4", color="gray.900"),
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="total_hours",
                                fill="#dc2626",
                                stroke="#b91c1c",
                                stroke_width=2,
                                radius=[4, 4, 0, 0]
                            ),
                            rx.recharts.x_axis(data_key="week"),
                            rx.recharts.y_axis(),
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                            rx.recharts.tooltip(
                                cursor={"fill": "transparent"}
                            ),
                            data=State.weekly_chart_data,
                            width="100%",
                            height=350,
                            margin={"top": 20, "right": 20, "bottom": 20, "left": 20}
                        ),
                        spacing="4",
                        width="100%"
                    ),
                    size="3",
                    width="100%"
                ),
                columns="2",
                spacing="4",
                margin_bottom="8",
                width="100%"
            ),

            # Activities List
            activities_list(),

            spacing="4",
            width="100%"
        ),
        size="4",
        background="linear-gradient(to bottom, #f9fafb, #ffffff)",
        min_height="100vh",
        padding="6"
    )


def activity_popup() -> rx.Component:
    """Activity details popup dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title(State.selected_activity_name),
                rx.vstack(
                    rx.hstack(
                        rx.text("Distance:", weight="bold", color="gray.600"),
                        rx.text(f"{State.selected_activity_distance} km", color="gray.900"),
                        justify="between",
                        width="100%"
                    ),
                    rx.hstack(
                        rx.text("Pace:", weight="bold", color="gray.600"),
                        rx.text(f"{State.selected_activity_pace} min/km", color="gray.900"),
                        justify="between",
                        width="100%"
                    ),
                    spacing="3",
                    width="100%"
                ),
                rx.dialog.close(
                    rx.button("Close", on_click=State.close_activity_popup),
                ),
                spacing="4"
            ),
            max_width="400px"
        ),
        open=State.show_activity_popup
    )

def loading_page() -> rx.Component:
    """Loading page component."""
    return rx.center(
        rx.vstack(
            rx.spinner(size="3", color="blue"),
            rx.text("Loading Strava data...", size="4", color="gray.600"),
            spacing="4"
        ),
        height="100vh",
        background="white"
    )


def index() -> rx.Component:
    """Main page component."""
    return rx.fragment(
        rx.cond(
            State.loading,
            loading_page(),
            dashboard()
        ),
        activity_popup()
    )


app = rx.App(
    style={
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "background": "white"
    }
)
app.add_page(index, route="/", title="Strava Analytics", on_load=State.load_data)