import os
import functools
import tempfile
import base64
import traceback
import json

import joblib
import numpy as np
import matplotlib
import arviz as az
import requests

from tornado.ioloop import IOLoop
import tornado.web
import tornado.escape

from astropy.time import Time
from astropy.table import Table
from astropy.io import ascii

from utils import parse_csv
from fit import fit_lc
from nmma_process import skyportal_input_to_nmma

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log("nmma_analysis_service")

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use("Agg")
rng = np.random.default_rng()

default_analysis_parameters = {
    "prior_directory": "/home/wkiendrebeogo/Projets/LVK-collaboration/nmma-skyportal/priors",
    "svdmodel_directory": "/home/wkiendrebeogo/Projets/NMMA/nmma/svdmodels/",
    "sampler": "pymultinest",
}


def upload_analysis_results(results, data_dict, request_timeout=60):
    """
    Upload the results to the webhook.
    """

    log("Uploading results to webhook")
    if data_dict["callback_method"] != "POST":
        log("Callback URL is not a POST URL. Skipping.")
        return
    url = data_dict["callback_url"]
    try:
        _ = requests.post(
            url,
            json=results,
            timeout=request_timeout,
        )
    except requests.exceptions.Timeout:
        # If we timeout here then it's precisely because
        # we cannot write back to the SkyPortal instance.
        # So returning something doesn't make sense in this case.
        # Just log it and move on...
        log("Callback URL timedout. Skipping.")
    except Exception as e:
        log(f"Callback exception {e}.")


def run_nmma_model(data_dict):
    """
    Use `nmma` to fit data to a model with name `model_name`.
    For this analysis, we expect the `inputs` dictionary to have the following keys:
       - model: the name of the model to fit to the data
       - photometry: the photometry to fit to the model (in csv format)
    Other analysis services may require additional keys in the `inputs` dictionary.
    """
    analysis_parameters = data_dict["inputs"].get(
        "analysis_parameters", data_dict["inputs"]
    )
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}

    model_name = analysis_parameters.get("model")
    # cand_name = analysis_parameters.get("object_id")
    prior_dir = analysis_parameters.get("prior_directory")
    svdmodel_dir = analysis_parameters.get("svdmodel_directory")
    interpolation_type = analysis_parameters.get("interpolation_type")
    sampler = analysis_parameters.get("sampler")

    # read csv file from nmma process
    data = skyportal_input_to_nmma(data_dict["inputs"]["photometry"])

    # Create a temporary file to save data in nmma csv format
    plotdir = os.path.abspath("..") + "/" + os.path.join("nmma_output")
    if not os.path.isdir(plotdir):
        os.makedirs(plotdir)

    # plotdir = tempfile.mkdtemp()
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", dir=plotdir, mode="w"
    ) as outfile:
        Data = Table()
        Data["jd"] = data["jd"]
        Data["mag"] = data["mag"]
        Data["mag_unc"] = data["mag_unc"]
        Data["filter"] = data["filter"]
        Data["limmag"] = data["limmag"]
        Data["programid"] = data["programid"]

        df = Data.to_pandas()
        df.to_csv(outfile)

        # infile take the  photometry csv file readable by nmma format
        # Parses a file format with a single candidate
        infile = outfile.name
        nmma_data = parse_csv(infile)

        fit_result = fit_lc(
            model_name,
            cand_name,
            nmma_data,
            prior_dir,
            svdmodel_dir,
            interpolation_type,
            sampler,
        )

        return fit_result


"""
result = (
posterior_samples,
bestfit_params,
bestfit_lightcurve_magKN_KNGRB,
log_bayes_factor,
nmma_input_file,
outfile,
data_out,
plot_data,
local_temp_files,)

"""
