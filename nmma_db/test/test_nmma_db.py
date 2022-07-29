import os
import pandas as pd
import numpy as np

from utils import parse_csv
from fit import fit_lc


infile = "../data/kilonova_BNS_lc.csv"

# Read and conver csv file from
nmma_data = parse_csv(infile)


model_name = "Bu2019lm"
cand_name = "kilonova_BNS_lc"

prior_directory = "../../priors"
svdmodel_directory = "/home/wkiendrebeogo/Projets/NMMA/nmma/svdmodels/"
interpolation_type = "tensorflow"  # "sklearn_gp"
sampler = "pymultinest"

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
