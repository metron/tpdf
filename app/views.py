import os
from glob import glob
from urllib.parse import quote

import aiohttp_jinja2
from aiohttp import web

from app.tpdf import TPdf, FILES


class ResponseFile(web.Response):
    def __new__(cls, file_name, file_body):
        headers = {
            "Content-Type": "application/pdf; charset='utf-8'",
            "Content-Disposition": "inline; filename*=UTF-8''{}".format(
                quote(file_name, encoding="utf-8"))
        }
        return web.Response(body=file_body, headers=headers)


@aiohttp_jinja2.template("index.html")
async def index(request):
    only_dirs = [f for f in os.listdir(FILES) if not os.path.isfile(os.path.join(FILES, f))]
    return {"dirs": only_dirs}


@aiohttp_jinja2.template("positioning.html")
async def positioning(request):
    tpdf = TPdf()
    # дефолтные параметры
    in_data = {
        "pdf_name": "ClearPage",
        "page_num": "1",
    }
    in_data.update(dict(request.query))
    fields = tpdf.load_fields_from_file(name=in_data["pdf_name"], to_front=True)
    fonts = [os.path.basename(filename)[:-4] for filename in glob(os.path.join(tpdf.FONTS, "*.ttf"))]
    in_data.update({"fields": fields, "fonts": fonts})
    return in_data


async def save_form_fields(request):
    rq = await request.json()
    return TPdf.save_fields_to_file(rq["pos"])


async def get_file(request):
    pdf_name = request.query["pdf_name"]
    tpdf = TPdf()
    file = tpdf.get_pdf(pdf_name, b64="False", fill_x=True)
    return ResponseFile(pdf_name, file)


async def example(request):
    # набор данных для генерации комплекта документов
    data = {
        "last_name": "Иванова",
        "first_name": "Мария",
        "middle_name": "Иванова",
        "gender": "Ж",
        "birth_date": "01.01.2000",
        "birth_place": "г.Москва",
        "registration": "г.Москва, ул. Полковника Исаева, дом 17, кв 43",
        "1_work": "Радистка 3 категории, в/ч 89031",
        "2_work": "Радистка 1 категории, в/ч 17043",
        "3_work": "Командир отделения радистов, в/ч 17043 главного управления разведки комитета государственной безопасности республики Беларусь.",
    }

    # перечень документов в комплекте
    complete = [
        ("ZayavlenieNaZagranpasport", 1),
        ("ClearPage", 1),
        ("ZayavlenieNaZagranpasport", 1),
    ]

    # загружаем данные в основной класс и получаем комплект документов в pdf
    tpdf = TPdf(**data)
    # можно сгенерировать один файл или комплект документов
    # file = tpdf.get_pdf("ZayavlenieNaZagranpasport ", b64="False")
    file = tpdf.get_complete(complete, b64="False")

    return ResponseFile("ZayavlenieNaZagranpasport.pdf", file)
