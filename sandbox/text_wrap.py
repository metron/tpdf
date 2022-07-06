import io
from datetime import datetime as dt
from typing import Generator

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from libs.tpdf import TPdf


def word_wrap(text: str, width: int, canvas: 'canvas.Canvas') -> \
        Generator[str, None, None]:
    """Делит text на части, если текст не помещается в width

    Args:
        text: текст
        width: ширина поля
        canvas: canvas

    Возвращает подстроки максимальной длины, не превышающей заданную ширину
        width, разбиение на подстроки по пробелам
    """
    while True:
        tail = ''
        tail_words = []
        while canvas.stringWidth(text) > width:
            words = text.split()
            if len(words) > 1:
                # перенос по словам
                text = ' '.join(words[:-1])
                tail_words = words[-1:] + tail_words
            else:
                # перенос по буквам
                tail = text[-1:] + tail
                text = text[:-1]
                # если даже одна буква не помещается
                if not text:
                    text = ' '.join([tail[1:], ] + tail_words).strip()
                    yield tail[:1]
        yield text
        # выходим, если хвост пустой
        text = ' '.join([tail, ] + tail_words).strip()
        if not text:
            break


if __name__ == '__main__':
    text = """Спустя два дня последний класс школы СП ШЦ-401 весело рассаживался под прозрачным куполом гигантского вагона Спиральной Дороги. Едва поезд набрал скорость, в центральном проходе появился Кими и объявил, что он готов читать реферат. Послышались энергичные протесты. Ученики доказывали, что не хватит внимания — слишком интересно смотреть по сторонам. Учитель примирил всех советом прослушать реферат в середине пути, когда поезд будет пересекать фруктовый пояс шириной около четырехсот километров, — это два часа хода. Когда потянулись бесконечные, геометрически правильные ряды деревьев на месте бывшей пустынной степи Декана, Кими установил в проходе маленький проектор и направил на стенку салона цветные лучи иллюстраций. Юноша говорил об открытии спирального устройства вселенной, после которого смогли разрешить задачу сверхдальних межзвездных перелетов. О биполярном строении мира математики знали еще в ЭРМ, но физики того времени запутали вопрос наивным представлением об антивеществе."""
    width = 100
    print(len(text))

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    start = dt.now()
    a = list(word_wrap(text, width, can))
    print(a)
    end = dt.now()
    print(start)
    print(end)
    print(end - start)

    start = dt.now()
    b = list(TPdf.text_wrap(text, width, can))
    print(b)
    end = dt.now()
    print(start)
    print(end)
    print(end - start)

    assert (a == b)
