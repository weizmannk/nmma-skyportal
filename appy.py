import os
import functools
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

import tempfile
import shutil
from astropy.time import Time
from astropy.table import Table
from astropy.io import ascii

from utils.util import parse_csv
from fit import fit_lc
from utils.nmma_process import skyportal_input_to_nmma

from utils.log import make_log
#from baselayer.app.env import load_env

#_, cfg = load_env()

log = make_log("nmma_analysis_service")

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use("Agg")
rng = np.random.default_rng()

default_analysis_parameters = {"source": "Bu2019lm", "fix_z": False}

infile =f"{os.path.dirname(os.path.realpath('__file__'))}/data/kilonova_BNS_lc.csv"

cand_name = "kilonova_BNS_lc"


data_dict = {
    "inputs": {
        "photometry": infile,
        "object_id": cand_name,
    }
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


def convert_csv(data_dict):

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
    # And makes sure thate the times is in correct format
    # We need to convert the time format mjd to the format expected by of session so in jd
    # the utils.py  file need jd format which will be convert in isot
    # Rename Columns from skyportal to nmma format
    # skyportal_col = ["mjd", "magerr", "limiting_mag", "instrument_name", obj_id]

    try:
        rez = {"status": "failure", "message": "", "analysis": {}}
        data = Table.read(data_dict["inputs"]["photometry"], format="ascii.csv")

        # data.rename_column("magerr", "mag_unc")
        # data.rename_column("limiting_mag", "limmag")
        # data.rename_column("instrument_name", "programid")
        for col in data.columns:
            if col == "magerr":
                data.rename_column("magerr", "mag_unc")

            elif col == "limmiting_mag":
                data.rename_column("limiting_mag", "limmag")

            elif col == "instrument_name":
                data.rename_column("instrument_name", "programid")

        # convert time in julien day format (jd)
        data["jd"] = Time(data["jd"], format="mjd").jd
        # data.rename_column("mjd", "jd")

        # Rename filter
        switcher = {1: "ztfg", 2: "ztfr", 3: "ztfi"}
        for filt in switcher.values():
            index = np.where(data["filter"] == filt)

            if filt == "ztfg":
                data["filter"][index] = "g"
            elif filt == "ztfr":
                data["filter"][index] = "r"
            elif filt == "ztfi":
                data["filter"][index] = "i"
            else:
                data["filter"][index] = filt

        data = data.filled()
        data.sort("jd")

    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        return rez

    return data


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

    model_name = analysis_parameters.get("source")
    fix_z = analysis_parameters.get("fix_z") in [True, "True", "t", "true"]
    cand_name = analysis_parameters.get("object_id")
    #prior_directory = analysis_parameters.get("prior_directory")
    #svdmodel_directory = analysis_parameters.get("svdmodel_directory")
    #interpolation_type = analysis_parameters.get("interpolation_type")
    #sampler = analysis_parameters.get("sampler")

    # read data and create a cvs file expecte to nmma 
    rez = {"status": "failure", "message": "", "analysis": {}}
    
    data = convert_csv(data_dict)
    

    try:
        #data = Table.read(data_dict["inputs"]["photometry"], format='ascii.csv')
        if fix_z: 
            redshift = Table.read(data_dict["inputs"]["redshift"], format='ascii.csv')
            z = redshift['redshift'][0]
        else: z = None

    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
   
    local_temp_files = []
    try:
        # Create a temporary file to save data in nmma csv format 
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w"
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
            outfile.flush()

            local_temp_files.append(outfile.name)
            
            # infile take the  photometry csv file readable by nmma format
            # Parses a file format with a single candidate
            nmma_data = parse_csv(outfile.name)
            # local_temp_files.append(outfile.name)
            # Fitting model model result

            (   inference_data,
                plot_data, 
                fit_result
            ) = fit_lc(
                model_name,
                cand_name,
                nmma_data,
                fix_z,
                z,
            )

            if fit_result.success:
                fit_result.update({"source": model_name, "object_id": cand_name})

                f = tempfile.NamedTemporaryFile(
                    suffix=".joblib", prefix="results_", delete=False
                )
                f.close()
                #outfile.flush()
                local_temp_files.append(f.name)
                
                joblib.dump(fit_result, outfile.name, compress=3)
                result_data = base64.b64encode(open(outfile.name, "rb").read())
                
                analysis_results = {
                    "inference_data": {"format": "netcdf4", "data": inference_data},
                    "plots": [{"format": "png", "data": plot_data}],
                    "results": {"format": "joblib", "data": result_data},
                }
                rez.update(
                    {
                    "analysis": analysis_results,
                    "status": "success",
                    "message": f" Inference results of inference with "
                    + r"$\log(bayes-factor)$"
                    + f" = { fit_result.json_result['log_bayes_factor']}",
                    }
                )
                rez.update({"status": "failure", "message": "model failed to converge"})

    except Exception as e:
        log(f"Exception while running the model: {e}")
        log(f"{traceback.format_exc()}")
        rez.update({"status": "failure", "message": f"problem running the model {e}"})
    finally:
        # clean up local files
        for f in local_temp_files:
            try:
                os.remove(f)
            except:  # noqa E722
                pass
    return rez

#result = run_nmma_model(data_dict)



class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def error(self, code, message):
        self.set_status(code)
        self.write({"message": message})

    def get(self):
        self.write({"status": "active"})

    def post(self):

        #Analysis endpoint which sends the `data_dict` off for
        #processing, returning immediately. The idea here is that
        #the analysis model may take awhile to run so we

        try:
            data_dict = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            err = traceback.format_exc()
            log(f"JSON decode error: {err}")
            return self.error(400, "Invalid JSON")

        required_keys = ["inputs", "callback_url", "callback_method"]
        for key in required_keys:
            if key not in data_dict:
                log(f"missing required key {key} in data_dict")
                return self.error(400, f"missing required key {key} in data_dict")

        def nmma_analysis_done_callback(
            future,
            logger=log,
            data_dict=data_dict,
        ):

            #Callback function for when the nmma analysis service #is done.
            #Sends back results/errors via the callback_url.
            #This is run synchronously after the future completes
            #so there is no need to await for `future`.

            try:
                result = future.result()
            except Exception as e:
                # catch all the exceptions and log them,
                # try to write back to SkyPortal something
                # informative.
                logger(f"{str(future.exception())[:1024]} {e}")
                result = {
                    "status": "failure",
                    "message": f"{str(future.exception())[:1024]}{e}",
                }
            finally:
                upload_analysis_results(result, data_dict)

        runner = functools.partial(run_nmma_model, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(nmma_analysis_done_callback)

        return self.write(
            {"status": "pending", "message": "nmma_analysis_service: analysis started"}
        )



def make_app():
    return tornado.web.Application(
        [
            (r"/analysis/demo_analysis", MainHandler),
        ]
    )

# Theo process
if __name__ == "__main__":
    nmma_analysis = make_app()
    if 'PORT' in os.environ:
        port = int(os.environ['PORT'])
    else:
        port = 6901
    nmma_analysis.listen(port)
    log(f"NMMA Service Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()


"""


if __name__ == "__main__":
    nmma_analysis = make_app()
    port = cfg["analysis_services.nmma_analysis_service.port"]
    nmma_analysis.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start() 
"""
