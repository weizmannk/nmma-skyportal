import os
import pandas as pd
import numpy as np

from utils import parse_csv
from fit import fit_lc


infile = "../data/lc_ZTF21abdpqpq_forced1_stacked0.csv"

# Read and conver csv file from
# nmma_data = parse_csv(infile)


model_name = "Bu2019lm"
cand_name = "lc_ZTF21abdpqpq_forced1_stacked0"

prior_directory = "../../priors"
svdmodel_directory = "/home/wkiendrebeogo/Projets/NMMA/nmma/svdmodels/"
interpolation_type = "sklearn_gp"
sampler = "pymultinest"

data_dict = {
    "inputs": {
        "model": model_name,
        "photometry": infile,
        "object_id": cand_name,
        "interpolation_type": interpolation_type,
    }
}


(
    posterior_samples,
    bestfit_params,
    bestfit_lightcurve_magKN_KNGRB,
    log_bayes_factor,
    nmma_input_file,
    outfile,
) = fit_lc(
    model_name,
    cand_name,
    nmma_data,
    prior_directory,
    svdmodel_directory,
    interpolation_type,
    sampler,
)


fit_result = fit_lc(
    model_name,
    cand_name,
    nmma_data,
    prior_directory,
    svdmodel_directory,
    interpolation_type,
    sampler,
)


def myFunc(x, y):
    print("starting for " + str([x, y]))
    time.sleep(5)
    return x**2 + 2 * y


argsList = [(1, 2), (3, 4), (5, 6), (7, 8)]
result = joblib.Parallel(n_jobs=2, prefer="processes")(
    joblib.delayed(myFunc)(*args) for args in argsList
)
print(result)
