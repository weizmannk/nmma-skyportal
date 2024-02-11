import subprocess
import sys
import os
import json
import base64

import arviz as az
import numpy as np
from astropy.time import Time
from astropy.table import Table
from scipy.optimize import OptimizeResult
import tempfile
import shutil
import bilby
from nmma.em.io import loadEvent
from lightcurves_model import get_bestfit_lightcurve
from util import check_and_remove_non_detection, plot_bestfit_lightcurve

from log import make_log

log = make_log("nmma_analysis_service")


def fit_lc(nmma_data, analysis_parameters, z=None):

    model_name = analysis_parameters.get("source")
    object_id = analysis_parameters.get("object_id")

    label = f"{object_id}_{model_name}"

    fix_z = analysis_parameters.get("fix_z") in [True, "True", "t", "true"]
    tmin = analysis_parameters.get("tmin")
    tmax = analysis_parameters.get("tmax")
    dt = analysis_parameters.get("dt")
    nlive = analysis_parameters.get("nlive")
    error_budget = str(analysis_parameters.get("error_budget"))
    Ebv_max = analysis_parameters.get("Ebv_max")
    sampler = analysis_parameters.get("sampler")
    interpolation_type = analysis_parameters.get("interpolation_type")

    trigger_time_heuristic = analysis_parameters.get("trigger_time_heuristic")
    fit_trigger_time = analysis_parameters.get("fit_trigger_time")
    remove_nondetections = analysis_parameters.get("remove_nondetections")

    local_only = analysis_parameters.get("local_only")
    prior_directory = analysis_parameters.get("prior_directory")
    svdmodel_directory = analysis_parameters.get("svdmodel_directory")

    # we will need to write to temp files
    # locally and then write their contents
    # to the results dictionary for uploading
    local_temp_files = []
    plotdir = tempfile.mkdtemp()
    plotName = os.path.join(plotdir, f"{label}_lightcurves.png")

    inference_data = None
    plot_data = None
    fit_result = None

    t0 = 0
    if fit_trigger_time:
        # Set to earliest detection in preparation for fit
        for line in nmma_data:
            if np.isinf(float(line[3])):
                continue
            else:
                trigger_time = Time(line[0], format="isot").mjd
                break
    elif trigger_time_heuristic:
        # One day before the first non-zero point
        for line in nmma_data:
            if np.isinf(float(line[3])):
                continue
            else:
                trigger_time = Time(line[0], format="isot").mjd - 1
                break
    else:
        # Set the trigger time
        trigger_time = t0

    # GRB model requires special values so lightcurves can be generated without NMMA running into timeout errors.
    if model_name == "TrPi2018":
        tmin = 0.01
        tmax = 7.01
        dt = 0.35

    try:
        prior = f"{prior_directory}/{model_name}.prior"
        if not os.path.isfile(prior):
            log(f"Prior file for model {source} does not exist")
            return
        priors = bilby.gw.prior.PriorDict(prior)
        if fix_z:
            if z is not None:
                from astropy.coordinates.distances import Distance

                distance = Distance(z=z, unit="Mpc")
                priors["luminosity_distance"] = distance.value
            else:
                raise ValueError("No redshift provided but `fix_z` requested.")

        priors.to_file(plotdir, model_name)
        prior = os.path.join(plotdir, f"{model_name}.prior")
        local_temp_files.append(prior)

        # output the data
        # in the format desired by NMMA
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".dat", prefix=f"{model_name}_", dir=plotdir, mode="w"
        ) as outfile:
            for line in nmma_data:
                outfile.write(
                    line[0] + " " + line[1] + " " + line[2] + " " + line[3] + "\n"
                )
            outfile.flush()

            data_out = loadEvent(outfile.name)

            # NMMA lightcurve fitting
            # triggered with a shell command
            command = [
                "lightcurve-analysis",
                "--model",
                model_name,
                "--svd-path",
                svdmodel_directory,
                "--outdir",
                plotdir,
                "--label",
                label,
                "--trigger-time",
                str(trigger_time),
                "--data",
                outfile.name,
                "--prior",
                prior,
                "--tmin",
                str(tmin),
                "--tmax",
                str(tmax),
                "--dt",
                str(dt),
                "--error-budget",
                error_budget,
                "--nlive",
                str(nlive),
                "--Ebv-max",
                str(Ebv_max),
                "--interpolation-type",
                interpolation_type,
                "--sampler",
                sampler,
                "--local-only",
            ]

            # Use Popen to execute the command and capture the output in real-time
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Read the output line by line as it becomes available
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    print(output.strip())

            # After the process is done, you can also capture any remaining output if needed
            stdout, stderr = process.communicate()
            if stdout:
                print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)

            posterior_file = os.path.join(
                plotdir, object_id + "_" + model_name + "_posterior_samples.dat"
            )
            json_file = os.path.join(
                plotdir, object_id + "_" + model_name + "_result.json"
            )

            if os.path.isfile(posterior_file):
                tab = Table.read(posterior_file, format="csv", delimiter=" ")
                inference = az.convert_to_inference_data(
                    tab.to_pandas().to_dict(orient="list")
                )
                f = tempfile.NamedTemporaryFile(
                    suffix=".nc", prefix="inferencedata_", dir=plotdir, delete=False
                )
                f.close()
                inference.to_netcdf(f.name)
                inference_data = base64.b64encode(open(f.name, "rb").read())

                with open(json_file, "r") as f:
                    result = json.load(f)

                # log_bayes_factor = lcDict["log_bayes_factor"]
                # log_evidence = lcDict["log_evidence"]
                # log_evidence_err = lcDict["log_evidence_err"]

                ##############################
                # Construct the best fit model
                ##############################
                plot_sample_times = np.arange(tmin, tmax + dt, dt)
                if (
                    model_name == "TrPi2018"
                    or model_name == "nugent-hyper"
                    or model_name == "salt2"
                ):
                    plot_sample_times = np.arange(0.01, 10.21, 0.2)

                data_out = check_and_remove_non_detection(
                    data_out, remove_nondetections=remove_nondetections
                )

                filters_to_analyze = list(data_out.keys())
                error_budget = [float(x) for x in error_budget.split(",")]
                error_budget = dict(
                    zip(filters_to_analyze, error_budget * len(filters_to_analyze))
                )

                print("Running with filters {0}".format(filters_to_analyze))

                (
                    bestfit_params,
                    bestfit_lightcurve_mag,
                    model_names,
                    models,
                    light_curve_model,
                ) = get_bestfit_lightcurve(
                    posterior_file=posterior_file,
                    model=model_name,
                    sample_times=plot_sample_times,
                    svd_path=svdmodel_directory,
                    interpolation_type=interpolation_type,
                    filters_to_analyze=filters_to_analyze,
                    sample_over_Hubble=False,
                    grb_resolution=7,
                    jet_type=0,
                    local_only=local_only,
                    bestfit=True,
                    error_budget=1,
                    outdir=plotdir,
                    label=label,
                )
                plot_bestfit_lightcurve(
                    data_out=data_out,
                    trigger_time=trigger_time,
                    filters_to_analyze=filters_to_analyze,
                    error_budget=error_budget,
                    plotName=plotName,
                    bestfit_params=bestfit_params,
                    bestfit_lightcurve_mag=bestfit_lightcurve_mag,
                    model_names=model_names,
                    models=models,
                    light_curve_model=light_curve_model,
                )
                plot_data = base64.b64encode(open(plotName, "rb").read())

            else:
                print("There is no directory to posterior file.")

    except Exception as e:
        print(e)

    # Use OptimizeResult from scipy to write and generate our results.
    else:
        if os.path.isfile(plotName):
            fit_result = OptimizeResult(
                success=True,
                message=f"{model_name} model has been used successfully to fit {object_id}.",
                bestfit_params=bestfit_params,
                bestfit_lightcurve_mag=bestfit_lightcurve_mag,
                json_result=result,
                data_out=data_out,
            )
        else:
            fit_result = OptimizeResult(
                success=False,
                message=f"Unfortunatly something goes wrong during {model_name} mdel to fit {object_id}.",
            )

    shutil.rmtree(plotdir)

    return (inference_data, plot_data, fit_result)
