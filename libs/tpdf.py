import base64
import io
import json
import os
from collections import namedtuple
from datetime import datetime as dt
from typing import Generator

from functools import cached_property
from pdfrw import PdfFileReader, PdfFileWriter, PageMerge
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(CUR_PATH, 'tpdf_templates')

FieldParams = namedtuple('FieldParams', 'x y name font_name font_size width')
page_size = A4
page_width = page_size[0]
page_height = page_size[1]
# https://stackoverflow.com/questions/139655/convert-pixels-to-points
corr = {'x': 205.0, 'y': 11.0, 'px_to_pt': 3/4, 'pt_to_px': 4/3}


class TPdf:

    def __init__(self, **kwargs):
        self.fields = {}
        self.fields.update(kwargs)
        self.fields = self.format_for_pdf(self.fields)
        self.documents = {}

    @staticmethod
    def load_fields_from_file(name='', to_front=False):
        """
        :param name: имя документа ( = имена файлов pdf, json)
        :param corr: нужно ли делать преобразование pdf координат в координаты
            html веб формы в пиксели?
        :return: словарь с набором параметров полей постранично
        """
        pdf_fields_path = os.path.join(FILES, name, 'fields.json')
        pdf_fields = json.load(open(pdf_fields_path, 'r'))
        for page in pdf_fields:
            if to_front:
                pdf_fields[page] = [
                    TPdf.convert_coord_to_front(FieldParams(*f))
                    for f in pdf_fields[page]
                ]
            else:
                pdf_fields[page] = [FieldParams(*f) for f in pdf_fields[page]]

        return pdf_fields

    @staticmethod
    def save_fields_to_file(new_pos):
        """
        :param pos: позиции полей + имя файла pdf, json
        :return: успех или не успех
        """
        file_name = new_pos.pop('file_name')
        pdf_fields_path = os.path.join(FILES, file_name, 'fields.json')
        res_positions = json.load(open(pdf_fields_path, 'r'))
        for page in new_pos:
            new_pos[page] = [
                TPdf.convert_coord_from_front(FieldParams(*f))
                for f in new_pos[page]
            ]
        res_positions.update(new_pos)
        # форматируем строку с данными, для красивого отображения в файле
        for page in res_positions:
            res_positions[page].sort(key=lambda field: field[1], reverse=True)
            res_positions[page] = [json.dumps(f) for f in res_positions[page]]
        # преобразовываем итоговый словарь с координатами в json-строку с
        # нужными переносами строк, убираем лишние кавычки и слэши и сохраняем
        # итоговую (параметры одного поля в одной строке) json-строку в файл
        new_pos_str = json.dumps(res_positions, indent=4).\
            replace('"[', '[').replace(']"', ']').replace('\\', '')
        with open(pdf_fields_path, 'w') as outfile:
            outfile.write(new_pos_str)
        return True

    @staticmethod
    def convert_coord_to_front(field: 'FieldParams') -> 'FieldParams':
        """Конвертирует координаты с координат pdf в координаты веб-интерфейса

        Для отображения полей на веб форме нужно корректировать значения координат
        и ширину полей, в файле хранятся координаты под вставку в pdf файл
        """
        scale = corr['pt_to_px']
        font_size = int(field.font_size * scale + 0.5)
        return FieldParams(
            x=field.x * scale + corr['x'],
            y=(page_height - field.y - field.font_size) * scale + corr['y'],
            name=field.name,
            font_name=field.font_name,
            font_size=font_size,
            width=field.width * scale,
        )

    @staticmethod
    def convert_coord_from_front(field: 'FieldParams') -> 'FieldParams':
        """Конвертирует координаты с фронта в координаты pdf"""
        scale = corr['px_to_pt']
        font_size = int(field.font_size * scale + 0.5)
        return FieldParams(
            x=round((field.x - corr['x']) * scale, 2),
            y=round(page_height - (field.y - corr['y']) * scale - font_size, 2),
            name=field.name,
            font_name=field.font_name,
            font_size=font_size,
            width=round(field.width * scale),
        )

    def add_document(self, name, fill_x=False):
        # подгружаем из файла параметры полей (координаты, размер шрифта и др.)
        pdf_fields = self.load_fields_from_file(name)

        # регистрируем все необходимые шрифты
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        last_font = ['DejaVuSans', 10]

        pdf_form_path = os.path.join(FILES, name, 'form.pdf')
        D_IMAGES = os.path.join(FILES, name, 'images')
        pdf_form = PdfFileReader(open(pdf_form_path, 'rb'))
        self.documents[name] = []
        # накладываем значения полей на страницы формы
        for page_number in range(len(pdf_form.pages)):
            page = pdf_form.getPage(page_number)
            page_num = str(page_number)
            # если на данной странице нужно впечатать какие-то поля
            if page_num in pdf_fields and pdf_fields[page_num]:
                # создаём объект бинарного файла в памяти
                packet = io.BytesIO()
                # create a new PDF with Reportlab
                # bottomup=0 - отсчёт Y делаем сверху вниз, как на фронте
                can = canvas.Canvas(packet, pagesize=page_size)
                can.setFont(*last_font)  # в момент создания страницы нужно
                # перебираем поля и заполняем их в pdf canvas
                for field in pdf_fields[page_num]:
                    # если шрифт изменился, то устанавливаем новое значение
                    new_font = [field.font_name, field.font_size]
                    if last_font != new_font:
                        last_font = new_font
                        can.setFont(*last_font)
                    # если это картинка, то рисуем её
                    if field.name.find('.') > -1:
                        img = ImageReader(os.path.join(D_IMAGES, field.name))
                        can.drawImage(img, field.x, field.y,
                                      width=field.width, mask='auto',
                                      preserveAspectRatio=True,
                                      anchor='se')
                    if fill_x:
                        # заполняем именем поля, если требуется для настройки
                        val = field.name
                        while can.stringWidth(val) > field.width and len(val):
                            val = val[:-1]
                    elif field.name in self.fields:
                        # если значение поля уже имеются, то берём его
                        val = str(self.fields[field.name])
                    else:
                        # в крайнем случае, пытаемся вычислить поле из property
                        val = getattr(self, field.name, '')
                    text = val if val else ''
                    # выводим данные (текст) в нужную позицию
                    y_margin = 0
                    for txt in self.text_wrap(text, field.width, can):
                        # есть не вместившийся текст, печатаем его на след строке
                        can.drawString(field.x, field.y - y_margin, txt)
                        y_margin += field.font_size * 1.2
                # сохраняем canvas и мерджим его на страницу шаблона (формы)
                can.save()
                packet.seek(0)
                PageMerge(page).add(PdfFileReader(packet).getPage(0)).render()
            # добавляем полученную страницу в свойство для отложенной сборки
            self.documents[name].append(page)

    @staticmethod
    def get_res(pdf_writer, b64='True'):
        """ Вывод результата используется в двух местах, поэтому вынес этот
        кусок кода в отдельную функцию """

        # результирующий pdf сохраняем также в бинайрный файл в памяти
        output_file = io.BytesIO()
        pdf_writer.write(output_file)
        output_file.seek(0)

        # преобразуем готовый pdf файл в base64, если необходимо
        if b64 == 'True':
            res = base64.b64encode(output_file.read()).decode('utf-8')
        else:
            res = output_file.read()
        return res

    def get_pdf(self, name, b64='True', fill_x=False):
        return self.get_complete([(name, 1), ], b64, fill_x)

    def get_complete(self, complete, b64='True', fill_x=False):
        """ Собираем несколько pdf файлов в один комплект документов
        :param complete: list of tuples список кортежей, каждый из кортежей
            содержит на первой позиции имя документа, на второй позиции
            количество копий документа (не страниц, а копий) которое
            необходимо напечатать. Список упорядочен в последовательности, в
            которой нужно напечатать документы
        :param fill_x: bool заполнять значения полей их именами
        :param b64: in ['True', 'False', 'Stream', ] - тип возвращаемых данных
            'True' - формат данных base64
            'False' - бинарные данные файла pdf
        """
        pdf_writer = PdfFileWriter()
        # перебираем документы из комплекта по именам
        for doc in complete:
            name = doc[0]  # имя документа
            count = doc[1]  # необходимое количество копий документа
            # если документ ещё не сформирован, то формируем его
            if name not in self.documents:
                self.add_document(name, fill_x)
            # добавляем нужное количество копий документа с именем name
            for i in range(count):
                # перебираем страницы документа и добавляем их в итоговый pdf
                for page in self.documents[name]:
                    pdf_writer.addPage(page)
        return self.get_res(pdf_writer, b64)

    @staticmethod
    def text_wrap(text: str, width: int, canvas: 'canvas.Canvas') -> \
            Generator[str, None, None]:
        """Делит text на части, если текст не помещается в width

        Args:
            text: текст
            width: ширина поля
            canvas: canvas

        Возвращает подстроки максимальной длины, не превышающей заданную ширину
            width, разбиение на подстроки по пробелам
        """
        last_space = 0
        text_start = 0
        word_len = 0
        cur_text_len = 0
        for i in range(len(text)):
            # длина очередного символа нужна заранее
            symbol_len = canvas.stringWidth(text[i])
            # запоминаем позицию пробела или вычисляем длину очередного слова
            if text[i] == ' ':
                last_space = i
                word_len = 0
            else:
                word_len += symbol_len

            # если длина части текста превысила допустимое значение, то возвращаем текст
            cur_text_len += symbol_len
            if cur_text_len > width:
                cur_text_len = word_len
                # если слово поместилось, то перенос по пробелу
                if text_start < last_space:
                    yield text[text_start:last_space]
                    text_start = last_space + 1
                # иначе переносим по буквам
                else:
                    yield text[text_start:i]
                    text_start = i
                    word_len = symbol_len
                    cur_text_len = symbol_len

        # возвращаем оставшийся кусочек текста
        yield text[text_start:]

    @staticmethod
    def format_for_pdf(data):
        """ Форматируем данные для впечатывания полей в pdf
        1. None заменяем на пустые строки
        2. Дату из вида 'ГГГГ-ММ-ДД' преобразует в 'ДД.ММ.ГГГГ'
        :param data: словарь значения которого надо отформатировать
        :return: изменённый словарь
        """
        for key in data.keys():
            # 1. Заменяем None на пустые строки
            if data[key] is None:
                data[key] = ''
            # 2. Форматируем дату и время
            if key.find('date') > -1:
                try:
                    data[key] = dt.strftime(
                        dt.strptime(data[key], '%Y-%m-%d'),
                        '%d.%m.%Y'
                    )
                except:
                    pass  # если формат даты другой, то не надо паниковать.

        return data

    @cached_property
    def fio(self):
        return ' '.join([
            self.fields.get('last_name', ''),
            self.fields.get('first_name', ''),
            self.fields.get('middle_name', ''),
        ])

    @cached_property
    def fio_short(self):
        return '{} {}.{}.'.format(
            self.fields.get('last_name', ''),
            self.fields.get('first_name', '')[:1],
            self.fields.get('middle_name', '')[:1],
        )

    @cached_property
    def now(self):
        return dt.now().strftime('%d.%m.%Y')

    @property
    def x(self):
        return 'X'

    @property
    def doc_type(self):
        return 'Паспорт РФ'
