import subprocess
import sys
import os
import json
import base64

import joblib
import arviz as az
import requests

import numpy as np
from astropy.time import Time
from astropy.table import Table
from scipy.optimize import OptimizeResult
import tempfile
import shutil
from pathlib import Path

from utils import get_bestfit_lightcurve, plot_bestfit_lightcurve

from nmma.em.utils import loadEvent


def fit_lc(
    model_name,
    cand_name,
    nmma_data,
    prior_directory,
    svdmodel_directory,
    interpolation_type,
    sampler,
):

    # Begin with stuff that may eventually replaced with something else,
    # such as command line args or function args.

    # Trigger time settings
    # t0 is used as the trigger time if both fit and heuristic are false.
    # Heuristic makes the trigger time 24hours before first detection.
    t0 = 1
    trigger_time_heuristic = False
    fit_trigger_time = True

    # Will select prior file if None
    # Can be assigned a filename to be used instead
    prior = None

    # Other important settings
    # cpus = 2
    nlive = 36
    error_budget = 1.0

    ##########################
    # Setup parameters and fit
    ##########################

    # Set the trigger time
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

    tmin = 0
    tmax = 7
    dt = 0.1
    Ebv_max = 0.5724

    # GRB model requires special values so lightcurves can be generated without NMMA running into timeout errors.
    if model_name == "TrPi2018":
        tmin = 0.01
        tmax = 7.01
        dt = 0.35

    # grb_resolution = 7
    # jet_type = 0
    # sampler = "pymultinest"
    # seed = 42

    # Set the prior file. Depends on model and if trigger time is a parameter.
    if prior is None:
        if model_name == "nugent-hyper":
            # supernova
            if fit_trigger_time:
                prior = f"{prior_directory}/ZTF_sn_t0.prior"
            else:
                prior = f"{prior_directory}/ZTF_sn.prior"
        elif model_name == "TrPi2018":
            # GRB
            if fit_trigger_time:
                prior = f"{prior_directory}/ZTF_grb_t0.prior"
            else:
                prior = f"{prior_directory}/ZTF_grb.prior"
        elif model_name == "Piro2021":
            # Shock cooling
            if fit_trigger_time:
                prior = f"{prior_directory}/ZTF_sc_t0.prior"
            else:
                prior = f"{prior_directory}/ZTF_sc.prior"
        elif model_name == "Bu2019lm":
            # KN
            if fit_trigger_time:
                prior = f"{prior_directory}/ZTF_kn_t0.prior"
            else:
                prior = f"{prior_directory}/ZTF_kn.prior"
        else:
            print("fit.py does not know of the prior file for model ", model_name)
            exit(1)

    # we will need to write to temp files
    # locally and then write their contents
    # to the results dictionary for uploading
    local_temp_files = []

    plotdir = tempfile.mkdtemp()
    # output the data
    # in the format desired by NMMA
    try:
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
            command = subprocess.run(
                "light_curve_analysis"
                + " --model "
                + model_name
                + " --svd-path "
                + svdmodel_directory
                + " --outdir "
                + plotdir
                + " --label "
                + cand_name
                + "_"
                + model_name
                + " --trigger-time "
                + str(trigger_time)
                + " --data "
                + outfile.name
                + " --prior "
                + prior
                + " --tmin "
                + str(tmin)
                + " --tmax "
                + str(tmax)
                + " --dt "
                + str(dt)
                + " --error-budget "
                + str(error_budget)
                + " --nlive "
                + str(nlive)
                + " --Ebv-max "
                + str(Ebv_max)
                + " --interpolation_type "
                + interpolation_type
                + " --sampler "
                + sampler,
                shell=True,
                capture_output=True,
            )
            sys.stdout.buffer.write(command.stdout)
            sys.stderr.buffer.write(command.stderr)

            ##############################
            # Construct the best fit model
            ##############################

            plot_sample_times_KN = np.arange(0.0, 30.0, 0.1)
            plot_sample_times_GRB = np.arange(30.0, 950.0, 1.0)
            plot_sample_times = np.concatenate(
                (plot_sample_times_KN, plot_sample_times_GRB)
            )
            
            posterior_file = os.path.join(
                plotdir, cand_name + "_" + model_name + "_posterior_samples.dat"
            )
            json_file = os.path.join(
                plotdir, cand_name + "_" + model_name + "_result.json"
            )

            if os.path.isfile(posterior_file):
                tab = Table.read(posterior_file, format='csv', delimiter=' ')
                print(tab)
                inference = az.convert_to_inference_data(
                    tab.to_pandas().to_dict(orient='list')
                )
                f = tempfile.NamedTemporaryFile(
                suffix=".nc", prefix="inferencedata_", dir=plotdir, delete=False
                )
                f.close()
                inference.to_netcdf(f.name)
                inference_data = base64.b64encode(open(f.name, 'rb').read())
               
                with open(json_file, "r") as f:
                    result  = json.load(f)

                #log_bayes_factor = lcDict["log_bayes_factor"]
                # log_evidence = lcDict["log_evidence"]
                # log_evidence_err = lcDict["log_evidence_err"]
                               
                print("*********************************")
                if os.path.isfile(json_file):
                    print("*********************************")

                (
                    posterior_samples,
                    bestfit_params,
                    bestfit_lightcurve_magKN_KNGRB,
                ) = get_bestfit_lightcurve(
                    model_name,
                    posterior_file,
                    svdmodel_directory,
                    plot_sample_times,
                    interpolation_type=interpolation_type,
                )

                # if fit_trigger_time:
                #    trigger_time += bestfit_params['KNtimeshift']

                plotName = os.path.join(plotdir, f"{model_name}_lightcurves.png")
                plot_bestfit_lightcurve(
                    outfile.name,
                    bestfit_lightcurve_magKN_KNGRB,
                    error_budget,
                    trigger_time,
                    plotName,
                
                )
                plot_data = base64.b64encode(open(plotName, "rb").read())
            
            else:
                print("There is no directory to posterior file.")
                
    except Exception as e:
        print(e)

    else: 
        if os.path.isfile(plotName):
            fit_result = OptimizeResult(
                success=True,
                message = f"{model_name} model has been used successfully to fit {cand_name}.",
                posterior_samples = posterior_samples,
                bestfit_params = bestfit_params,
                bestfit_lightcurve_magKN_KNGRB = bestfit_lightcurve_magKN_KNGRB,
                json_result = result,
                data_out = data_out,
            )
        else:
            fit_result = OptimizeResult(
                success=False,
                message=f"Unfortunatly something goes wrong during {model_name} mdel to fit {cand_name}.",
            )

    shutil.rmtree(plotdir)

    return (inference_data,  plot_data, fit_result)