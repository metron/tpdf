import logging
import os

import aiohttp_jinja2
import jinja2
from aiohttp import web

from handlers import tpdf

app = web.Application()

aiohttp_jinja2.setup(
    app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), "templates"))
)

logging.basicConfig(level=logging.DEBUG)

app.add_routes([
    web.get('/tpdf/positioning', tpdf.positioning),
    web.post('/tpdf/save_form_fields', tpdf.save_form_fields),
    web.get('/tpdf/get_file', tpdf.get_file),
    web.get('/tpdf/example', tpdf.example),
])

web.run_app(app, port=8001)
