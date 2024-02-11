# python zenodo_model_downloader.py --model="Bu2019lm" --filters=ztfr --svd-path='./svdmodels' --source='zenodo'

import re
import requests
from requests.exceptions import ConnectionError, HTTPError
import os
from os.path import exists
from os import makedirs
from pathlib import Path
import logging
from yaml import load, Loader
from tqdm import tqdm
from retrying import retry
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants and global variables
PERMANENT_DOI = "8039909"
DOI = ""
MODELS = {}


def get_models_home(models_home=None):
    if models_home is None:
        models_home = Path("./models")
    return Path(models_home)


def get_latest_zenodo_doi(permanent_doi):
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(
            f"https://zenodo.org/record/{permanent_doi}", headers=headers
        )
        response.raise_for_status()
        data = response.text.split("10.5281/zenodo.")[1]
        doi = re.findall(r"^\d+", data)[0]
        return doi
    except (ConnectionError, HTTPError) as e:
        raise ConnectionError(f"Could not retrieve DOI due to network error: {e}")
    except Exception as e:
        raise ValueError(f"Could not parse DOI: {e}")


def download_models_list(doi, models_home):
    try:
        response = requests.get(
            f"https://zenodo.org/record/{doi}/files/models.yaml", allow_redirects=True
        )
        response.raise_for_status()
        with open(Path(models_home, "models.yaml"), "wb") as f:
            f.write(response.content)
    except HTTPError as e:
        raise ConnectionError(f"Could not download models list: {e}")


def load_models_list(doi=None, models_home=None):
    models_home = get_models_home(models_home)
    if not exists(models_home):
        makedirs(models_home)

    used_local = False  # Add a flag to indicate whether local files are used
    if not exists(Path(models_home, "models.yaml")) or doi is not None:
        try:
            download_models_list(doi, models_home)
        except HTTPError as e:
            logger.warning("Using local models due to error: {}".format(e))
            used_local = True  # Set the flag to True if falling back to local files

    with open(Path(models_home, "models.yaml"), "r") as f:
        models = load(f, Loader=Loader)

    return models, used_local  # Return both models and the flag


def refresh_models_list(models_home=None):
    global MODELS
    models_home = get_models_home(models_home)
    if exists(Path(models_home, "models.yaml")):
        Path(models_home, "models.yaml").unlink()
    try:
        MODELS = load_models_list(DOI, models_home)
    except Exception as e:
        raise ValueError(f"Could not refresh models list: {e}")


# Constants for download retries
MAX_RETRIES = 5
WAIT_FIXED = 3000  # 3 seconds wait between retries
TIMEOUT = 60  # Timeout set to 60 seconds


@retry(stop_max_attempt_number=MAX_RETRIES, wait_fixed=WAIT_FIXED)
def download_file_with_retry(url, output_path):
    response = requests.get(url, stream=True, timeout=TIMEOUT)  # Adjusted timeout
    response.raise_for_status()  # Handles non-200 responses by raising HTTPError

    total_size_in_bytes = int(response.headers.get("content-length", 0))
    chunk_size = 1024  # 1 Kibibyte

    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
    with open(output_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            progress_bar.update(len(chunk))
            file.write(chunk)
    progress_bar.close()

    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        logger.error("Downloaded file size does not match expected content length.")
        raise Exception("File download incomplete.")


def get_model(
    models_home=None,
    model_name=None,
    filters=[],
    download_if_missing=True,
    filters_only=False,
):
    global MODELS

    if model_name is None:
        raise ValueError("model_name must be specified")

    if not MODELS:
        _, used_local = load_models_list(DOI, models_home)

    if model_name not in MODELS:
        raise ValueError(f"Model {model_name} not found in models list")

    # Construct the model's base URL
    base_url = f"https://zenodo.org/record/{DOI}/files"

    # Ensure the SVD path exists
    svd_path = Path(models_home) / model_name
    svd_path.mkdir(parents=True, exist_ok=True)

    # Download the model file if not downloading filters only
    if not filters_only:
        model_file_path = svd_path / f"{model_name}.pkl"
        if not model_file_path.exists() or download_if_missing:
            model_url = f"{base_url}/{model_name}.pkl"
            logger.info(f"Downloading model {model_name} from {model_url}")
            download_file_with_retry(model_url, model_file_path)

    # Download the filter files
    for filter_name in filters:
        filter_file_path = svd_path / f"{filter_name}.pkl"
        if not filter_file_path.exists() or download_if_missing:
            filter_url = f"{base_url}/{model_name}_{filter_name}.pkl"
            logger.info(f"Downloading filter {filter_name} from {filter_url}")
            download_file_with_retry(filter_url, filter_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download model data from Zenodo.")
    parser.add_argument(
        "--model", type=str, help="Name of the model to download", required=True
    )
    parser.add_argument(
        "--filters",
        type=str,
        help="List of filters to download",
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "--svd-path", type=str, help="Path to save downloaded files", required=True
    )
    parser.add_argument("--source", type=str, help="Source of the data", required=True)

    args = parser.parse_args()

    MODEL_NAME = args.model
    FILTERS = args.filters
    SVD_PATH = args.svd_path
    SOURCE = args.source

    try:
        DOI = get_latest_zenodo_doi(PERMANENT_DOI)
        models, used_local = load_models_list(DOI)
        if used_local:
            logger.info("Using local models list.")
        else:
            logger.info("Using models list from Zenodo.")

        # Example call to get_model
        get_model(
            models_home=SVD_PATH,
            model_name=MODEL_NAME,
            filters=FILTERS,
            download_if_missing=True,
        )
    except Exception as e:
        logger.error(f"Error occurred: {e}")
