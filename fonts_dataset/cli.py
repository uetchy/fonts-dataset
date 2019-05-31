import json
import multiprocessing as mp
import os
import shutil
import string
import subprocess
import sys
from glob import glob
from os import path

import click
import numpy
from fontTools.ttLib import TTFont
from google.protobuf import text_format
from PIL import Image, ImageDraw, ImageFont

from fonts_dataset.fonts_public_pb2 import FamilyProto

ROOT_DIR = path.join(path.dirname(__file__))
WORKING_DIR = path.join(ROOT_DIR, 'data')
CATALOG_PATH = path.join(WORKING_DIR, 'catalog.json')
DATA_DIR = path.join(WORKING_DIR, 'characters')
RAW_DATA_DIR = path.join(WORKING_DIR, 'raw', 'google-fonts')
LABELS = string.ascii_letters
IMAGE_WIDTH, IMAGE_HEIGHT = (32, 32)


def save_json(catalog):
    with open(CATALOG_PATH, 'w') as f:
        f.write(json.dumps(catalog))


def list_all_fonts():
    metadata_list = glob(path.join(RAW_DATA_DIR, '**/*/METADATA.pb'))
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


def generate_glyph_image(font):
    for index, label in enumerate(LABELS):
        output_path = path.join(DATA_DIR, str(index) + '_' + label, font['post_script_name'] + ".png")
        if path.exists(output_path):
            continue

        canvas = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "black")
        draw = ImageDraw.Draw(canvas)
        ifont = ImageFont.truetype(font['path'], IMAGE_WIDTH - 10)
        w, h = draw.textsize(label, font=ifont)
        draw.text(((IMAGE_WIDTH - w) / 2, (IMAGE_HEIGHT - h) / 2), label, font=ifont, fill="white")
        canvas.save(output_path)


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
    res = subprocess.run(['git', 'clone', 'https://github.com/google/fonts.git', RAW_DATA_DIR], stdout=subprocess.PIPE)
    sys.stdout.buffer.write(res.stdout)


@cli.command()
def gen_catalog():
    os.makedirs(WORKING_DIR, exist_ok=True)
    catalog = list_all_fonts()
    save_json(catalog)
    print('generated', CATALOG_PATH)
    print('number of fonts:', len(catalog))
    return catalog


@cli.command()
def gen_dataset():
    for index, label in enumerate(LABELS):
        os.makedirs(path.join(DATA_DIR, str(index) + '_' + label), exist_ok=True)
    with open(CATALOG_PATH) as f:
        catalog = json.loads(f.read())
    for font in catalog:
        name = font['post_script_name']
        filepath = font['path']
        print(name, filepath)
        try:
            generate_glyph_image(font)
        except OSError as e:
            print('Error', e)


if __name__ == '__main__':
    cli()
