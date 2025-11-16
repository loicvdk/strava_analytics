import reflex as rx

config = rx.Config(
    app_name="strava_dashboard",
    port=3001,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)