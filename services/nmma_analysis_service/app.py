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

from utils import parse_csv
from fit import fit_lc

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log("nmma_analysis_service")

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use("Agg")
rng = np.random.default_rng()


default_analysis_parameters = {
    "interpolation_type": interpolation_type,
    "svdmodel_dir": svdmodel_directory,
    "prior_directory": prior_directory,
    "interpolation_type": interpolation_type,
    "sampler": sampler,
}

data_dict = {
    "inputs": {"model": model_name, "photometry": nmma_data, "object_id": cand_name}
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
       - fix_z: whether to fix the redshift
       - photometry: the photometry to fit to the model (in csv format)
       - redshift: the known redshift of the object
    Other analysis services may require additional keys in the `inputs` dictionary.
    """
    analysis_parameters = data_dict["inputs"].get(
        "analysis_parameters", data_dict["inputs"]
    )
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}
    model = analysis_parameters.get("model")

    # fix_z = analysis_parameters.get("fix_z") in [True, "True", "t", "true"]

    # this example analysis service expects the photometry to be in
    # a csv file (at data_dict["inputs"]["photometry"]) with the following columns
    # - filter: the name of the bandpass
    # - mjd: the modified Julian date of the observation
    # - magsys: the mag system (e.g. ab) of the observations
    # - limiting_mag:
    # - magerr:
    # - flux: the flux of the observation
    # the following code transforms these inputs from SkyPortal
    # to the format expected by nmma.
    #
    rez = {"status": "failure", "message": "", "analysis": {}}
    try:
        data = Table.read(data_dict["inputs"]["photometry"], format="ascii.csv")
        data.rename_column("magerr", "mag_unc")
        data.rename_column("limiting_mag", "limmag")
        data.rename_column("instruments", "programid")
        # data["flux"].fill_value = 1e-6
        data = data.filled()
        data.sort("jd")

        # redshift = Table.read(data_dict["inputs"]["redshift"], format="ascii.csv")
        # z = redshift["redshift"][0]
    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        return rez

    # fitting data by using nmma
    fit_result = fit_lc(
        model_name,
        cand_name,
        nmma_data,
        prior_directory,
        svdmodel_directory,
        interpolation_type,
        sampler,
    )

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
