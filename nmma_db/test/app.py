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
       - fix_z: whether to fix the redshift
       - photometry: the photometry to fit to the model (in csv format)
       - redshift: the known redshift of the object
    Other analysis services may require additional keys in the `inputs` dictionary.
    """
    analysis_parameters = data_dict["inputs"].get(
        "analysis_parameters", data_dict["inputs"]
    )
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}

    model_name = analysis_parameters.get("model")
    # cand_name = analysis_parameters.get("object_id")
    prior_directory = analysis_parameters.get("prior_dir")
    svdmodel_directory = analysis_parameters.get("svdmodel_dir")
    interpolation_type = analysis_parameters.get("interpolation_type")
    sampler = analysis_parameters.get("sampler")

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
        data.rename_column("instrument_name", "programid")

        if data["filter"] == "ztfr":
            data["filter"] = "r"
        elif data["filter"] == "ztfg":
            data["filter"] = "g"
        elif data["filter"] == "ztfi":
            data["filter"] = "i"
        else:
            data["filter"] = data["filter"]

        # convert time in julien day format
        jd = Time(data["mjd"], format="mjd").jd
        data["jd"] = jd

        data = data.filled()
        data.sort("jd")

        # Object ID
        cand_name = data["obj_id"]

    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        return rez

    # Create a temporary file to save data in nmma csv format
    plotdir = os.path.abspath("..") + "/" + os.path.join("nmma_output")
    if not os.path.isdir(plotdir):
        os.makedirs(plotdir)
    # plotdir = tempfile.mkdtemp()

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", dir=plotdir, mode="w"
    ) as outfile:
        Table(
            {
                "jd": data["jd"],
                "mag": data["mag"],
                "mag_unc": data["mag_unc"],
                "filter": data["filter"],
                "limmag": data["limmag"],
                "programid": data["programid"],
            }
        ).write(outfile, overwrite=True, format="ascii.csv")

        # infile take the  photometry csv file readable by nmma format
        # Parses a file format with a single candidate
        infile = outfile.name
        nmma_data = parse_csv(infile)

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
