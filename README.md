# Fonts Dataset

## Create Dataset

```
git submodule init
git submodule update
poetry install
python3 -m fonts_dataset.cli download-dataset
python3 -m fonts_dataset.cli gen-catalog
python3 -m fonts_dataset.cli gen-dataset
```
