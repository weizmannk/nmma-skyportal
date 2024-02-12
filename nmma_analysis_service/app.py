## python -m nmma.utils.models --model="Bu2019lm" --filters=ztfr,ztfg,ztfi --svd-path='./svdmodels' --source='zenodo'

import os
import functools
import tempfile
import base64
import traceback
import json

import requests
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Set backend for matplotlib
import arviz as az
import joblib
from astropy.table import Table

from tornado.ioloop import IOLoop
import tornado.web
import tornado.escape

from fit import fit_lc
from nmma_process import skyportal_input_to_nmma, parse_csv
from log import make_log

# Set the backend for matplotlib to ensure it can render plots headlessly
matplotlib.use("Agg")
rng = np.random.default_rng()

ALLOWED_MODELS = [
    "Bu2019lm",
    "Me2017",
    "Piro2021",
    "nugent-hyper",
    "TrPi2018",
    "Bu2022Ye",
]

# Default analysis parameters
infile = f"{os.path.dirname(os.path.realpath('__file__'))}/kilonova_BNS_lc.csv"
prior_dir = os.path.join(os.path.dirname(os.path.realpath('__file__')), "..", "nmma", "priors")
svdmodel_dir = os.path.join(os.path.dirname(os.path.realpath('__file__')), "svdmodels")

default_analysis_parameters = {
    "fix_z": False,
    "tmin": 0.01,
    "tmax": 7,
    "dt": 0.1,
    "nlive": 36,
    "error_budget": 1.0,
    "Ebv_max": 0.5724,
    "interpolation_type": "sklearn_gp",
    "sampler": "pymultinest",
    "fit_trigger_time": True,
    "trigger_time_heuristic": False,
    "remove_nondetections": False,
    "local_only": False,
    "prior_directory": prior_dir,
    "svdmodel_directory": svdmodel_dir,
}

# Construct input data dictionary, callback_url, and callback_method
data_dict = {
    "inputs": {
        "photometry": infile,
        "object_id": "kilonova_BNS_lc",
        "source": "Piro2021",  
    },
    "callback_url": "http://localhost:5000",  
    "callback_method": "POST"
}


# Configure logging
log = make_log("nmma_analysis_service")


def upload_analysis_results(results, data_dict, request_timeout=60):
    """
    Upload the results to the webhook specified in data_dict.
    """
    log("Uploading results to webhook")
    url = data_dict.get("callback_url")
    if not url or data_dict.get("callback_method") != "POST":
        log("Invalid callback URL or method. Skipping upload.")
        return

    try:
        _ = requests.post(url, json=results, timeout=request_timeout)
    except requests.exceptions.Timeout:
        log("Callback URL timed out. Skipping.")
    except Exception as e:
        log(f"Callback exception: {e}.")


def run_nmma_model(data_dict):
    """
    Fit data to a specified model using NMMA and upload results.
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
    object_id = analysis_parameters.get("object_id")

    # Initialize response structure
    response = {"status": "failure", "message": "", "analysis": {}}
    local_temp_files = []
    try:
        # Convert input data to NMMA format and fit model
        data = skyportal_input_to_nmma(analysis_parameters)
        z = None
        if fix_z:
            z = Table.read(data_dict["inputs"]["redshift"], format="ascii.csv")[
                "redshift"
            ][0]

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w"
        ) as outfile:
            data.write(outfile, format="csv")

            # Flush and close the file to ensure data is written to disk
            outfile.flush()
            os.fsync(outfile.fileno())
            outfile.close()

            local_temp_files.append(outfile.name)
            # Check if the file is not empty
            if os.path.getsize(outfile.name) > 0:
                print(f"Data successfully written to {outfile.name}")
                # Call parse_csv with the path to the temporary file
                nmma_data = parse_csv(outfile.name)
            else:
                print(f"Temporary file {outfile.name} is empty. Check the data Table.")

            # Fitting model model result
            inference_data, plot_data, fit_result = fit_lc(
                nmma_data, analysis_parameters, z
            )

            if fit_result.success:
                # Directly update fit_result with model name and object ID
                fit_result.update({"source": model_name, "object_id": object_id})

                with tempfile.NamedTemporaryFile(
                    suffix=".joblib", prefix="results_", delete=False
                ) as file:
                    file.flush()

                    joblib.dump(fit_result, file.name, compress=3)
                    result_data = base64.b64encode(open(file.name, "rb").read())

                    local_temp_files.append(file.name)

                    response.update(
                        {
                            "analysis": {
                                "inference_data": {
                                    "format": "netcdf4",
                                    "data": base64.b64encode(inference_data).decode(),
                                },
                                "plots": [
                                    {
                                        "format": "png",
                                        "data": base64.b64encode(plot_data).decode(),
                                    }
                                ],
                                "results": {"format": "joblib", "data": result_data},
                            },
                            "status": "success",
                            "message": f"Model {model_name} successfully fitted to {object_id} with "
                            + r"$\log(bayes-factor)$"
                            + f" = { fit_result.json_result['log_bayes_factor']}",
                        }
                    )

            else:
                log("Fit failed.")
                response.update(
                    {"status": "failure", "message": "Model fitting failed."}
                )

    except Exception as e:
        log(f"Exception while running the model: {traceback.format_exc()}")
        response.update(
            {"status": "failure", "message": f"Problem running the model: {e}"}
        )

    finally:
        # clean up local files
        for f in local_temp_files:
            try:
                os.remove(f)
            except:  # noqa E722
                pass
    return response


# result = run_nmma_model(data_dict)


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def error(self, code, message):
        self.set_status(code)
        self.write({"message": message})

    def get(self):
        self.write({"status": "active"})

    def post(self):
        """
        Analysis endpoint which sends the `data_dict` off for
        processing, returning immediately. The idea here is that
        the analysis model may take awhile to run so we
        need async behavior.
        """
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

        source = data_dict["inputs"].get("analysis_parameters", {}).get("source", None)
        if source is None:
            log("model not specified in data_dict.inputs.analysis_parameters")
            return self.error(
                400, "model not specified in data_dict.inputs.analysis_parameters"
            )
        elif source not in ALLOWED_MODELS:
            log(f"model {source} is not one of: {ALLOWED_MODELS}")
            return self.error(
                400, f"model {source} is not allowed, must be one of: {ALLOWED_MODELS}"
            )

        def nmma_analysis_done_callback(
            future,
            data_dict=data_dict,
        ):
            """
            Callback function for when the nmma analysis service is done.
            Sends back results/errors via the callback_url.

            This is run synchronously after the future completes
            so there is no need to await for `future`.
            """

            try:
                result = future.result()
            except Exception as e:
                # catch all the exceptions and print them,
                # try to write back to SkyPortal something
                # informative.
                log(f"{str(future.exception())[:1024]} {e}")
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


class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("OK")


def make_app():
    return tornado.web.Application(
        [
            (r"/analysis", MainHandler),
            (r"/health", HealthHandler),
        ]
    )


if __name__ == "__main__":
    nmma_analysis = make_app()
    if "PORT" in os.environ:
        port = int(os.environ["PORT"])
    else:
        port = 4003
    nmma_analysis.listen(port)
    log(f"NMMA Service Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
