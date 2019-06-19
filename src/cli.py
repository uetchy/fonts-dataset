import json
import multiprocessing as mp
import os
import shutil
import string
import subprocess
import sys
from glob import glob
from os import path
from xml.etree.ElementTree import parse

import click
import numpy
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from google.protobuf import text_format
from PIL import Image, ImageDraw, ImageFont

from fonts_dataset.fonts_public_pb2 import FamilyProto

ROOT_DIR = path.join(path.dirname(__file__), 'data')
PREPROCESSED_DIR = path.join(ROOT_DIR, 'preprocessed')
RAW_DIR = path.join(ROOT_DIR, 'raw', 'google-fonts')
RESULT_DIR = path.join(ROOT_DIR, 'generated')
CATALOG_PATH = path.join(RESULT_DIR, 'catalog.json')
BITMAP_DIR = path.join(RESULT_DIR, 'characters')
VECTOR_DIR = path.join(RESULT_DIR, 'vectors')

LABELS = string.ascii_letters
IMAGE_WIDTH, IMAGE_HEIGHT = (32, 32)


def save_json(catalog):
    with open(CATALOG_PATH, 'w') as f:
        f.write(json.dumps(catalog))


def list_all_fonts():
    metadata_list = glob(path.join(RAW_DIR, '**/*/METADATA.pb'))
    result = []

    for metadata_DIR in metadata_list:
        with open(metadata_DIR, 'rb') as data:
            metadata = text_format.Parse(data.read(), FamilyProto())

        if ('latin' or 'latin-ext') not in metadata.subsets:
            continue

        font_root = path.dirname(metadata_DIR)
        fonts = metadata.fonts
        for font in fonts:
            record = {
                'name': font.name,
                'full_name': font.full_name,
                'post_script_name': font.post_script_name,
                'category': metadata.category,
                'style': font.style,
                'weight': font.weight,
                'subsets': [x for x in metadata.subsets],
                'path': path.join(font_root, font.filename)
            }
            result.append(record)
    return result


# # https://shiromoji.hatenablog.jp/entry/2017/11/26/221902
def generate_glyph_image(font):
    for index, label in enumerate(LABELS):
        bitmap_output_path = path.join(BITMAP_DIR, str(index) + '_' + label, font['post_script_name'] + ".png")
        if path.exists(bitmap_output_path):
            continue

        # bitmap
        canvas = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "black")
        draw = ImageDraw.Draw(canvas)
        ifont = ImageFont.truetype(font['path'], IMAGE_WIDTH - 10)
        w, h = draw.textsize(label, font=ifont)
        draw.text(((IMAGE_WIDTH - w) / 2, (IMAGE_HEIGHT - h) / 2), label, font=ifont, fill="white")
        canvas.save(bitmap_output_path)

    # vector
    vector_output_path = path.join(PREPROCESSED_DIR, font['post_script_name'] + '.ttx')
    if path.exists(vector_output_path):
        return
    ttfont = TTFont(font['path'])
    glyph_set = ttfont.getGlyphSet()
    cmap = ttfont.getBestCmap()
    ttfont.saveXML(vector_output_path)
    ascender = ttfont['OS/2'].sTypoAscender
    descender = ttfont['OS/2'].sTypoDescender
    height = ascender - descender

    for index, label in enumerate(LABELS):
        glyph_name = cmap[ord(label)]
        glyph = glyph_set[glyph_name]
        width = glyph.width
        pen = RecordingPen()
        glyph.draw(pen)

        # [[x, y, isPenDown, isControlPoint, isContourEnd, isGlyphEnd], ...]
        matrix = []
        for command in pen.value:
            name = command[0]
            points = command[1]
            print('name:', name)
            print('points:', points)
            # if name == 'closePath':
            #     pass
            # if name == 'moveTo':
            #     matrix.append((points[0][0], points[0][1], 0, 0, 0, 0))
            # elif name == 'qCurveTo':
            #     matrix.append((points[0][0], points[0][1], 1, 1, 0, 0))
            #     matrix.append((points[1][0], points[1][1], 1, 0, 0, 0))
            # elif name == 'lineTo':
            #     matrix.append((points[1][0], points[1][1], 1, 0, 0, 0))

        os.exit()


def get_glyph(filename):
    doc = parse(filename)
    root = doc.getroot()

    glyph = root[13][17]
    return glyph


def inspect():
    doc = parse('./DroidSans.ttx')
    root = doc.getroot()

    glyph = root[13][17]
    meta = glyph.attrib
    contours = glyph.findall('contour')
    for k, v in meta.items():
        print(k, v)

    print('nb_contour', len(contours))
    for i, contour in enumerate(contours):
        print('iteration', i)
        points = [p.attrib for p in contour.getchildren()]
        for point in points:
            coord = (point['x'], point['y'])
            on_curve = point['on'] == '1'
            print(coord, on_curve)


@click.group()
def cli():
    pass


@cli.command()
def bootstrap():
    gftools_dir = path.join(ROOT_DIR, '..', 'third_party', 'gftools', 'Lib', 'gftools')
    shutil.copyfile(path.join(gftools_dir, 'fonts_public_pb2.py'), path.join(ROOT_DIR, 'fonts_public_pb2.py'))
    shutil.copyfile(path.join(gftools_dir, 'fonts_public.proto'), path.join(ROOT_DIR, 'fonts_public.proto'))


@cli.command()
def download_dataset():
    res = subprocess.run(['git', 'clone', 'https://github.com/google/fonts.git', RAW_DIR], stdout=subprocess.PIPE)
    sys.stdout.buffer.write(res.stdout)


@cli.command()
def gen_catalog():
    os.makedirs(RESULT_DIR, exist_ok=True)
    catalog = list_all_fonts()
    save_json(catalog)
    print('generated', CATALOG_PATH)
    print('number of fonts:', len(catalog))
    return catalog


@cli.command()
def gen_dataset():
    for index, label in enumerate(LABELS):
        os.makedirs(path.join(BITMAP_DIR, str(index) + '_' + label), exist_ok=True)
    os.makedirs(PREPROCESSED_DIR, exist_ok=True)
    with open(CATALOG_PATH) as f:
        catalog = json.loads(f.read())
    for font in catalog:
        name = font['post_script_name']
        filepath = font['path']
        print(name, filepath)
        try:
            generate_glyph_image(font)
        except OSError as e:
            print('Error:' + e)


if __name__ == '__main__':
    cli()
