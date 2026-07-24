# Getting the data

Download the "Online Retail II" dataset into `./data/`.

## Option A — Kaggle
1. https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci
2. Download and place `online_retail_II.csv` (or the `.xlsx`) in `./data/`.

## Option B — UCI ML Repository
https://archive.ics.uci.edu/dataset/502/online+retail+ii
Download `online_retail_II.xlsx` into `./data/`.

`build_features.py` auto-detects either `.csv` or `.xlsx` in `./data/`.
The raw file is gitignored; only the small cleaned Parquet gets committed for deploy.
