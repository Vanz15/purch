import reflex as rx

config = rx.Config(
    app_name="purch",
    plugins=[rx.plugins.SitemapPlugin(), rx.plugins.TailwindV4Plugin()],
)
