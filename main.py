import logging
import os

import aiohttp_jinja2
import jinja2
from aiohttp import web

from app import views

app = web.Application()

aiohttp_jinja2.setup(
    app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), "templates"))
)

logging.basicConfig(level=logging.DEBUG)

app.add_routes([
    web.get("/", views.index),
    web.static("/static", "static", show_index=True),
    web.get("/tpdf/positioning", views.positioning),
    web.post("/tpdf/save_form_fields", views.save_form_fields),
    web.get("/tpdf/get_file", views.get_file),
    web.get("/tpdf/example", views.example),
])

web.run_app(app, port=8001)
