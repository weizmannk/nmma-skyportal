import warnings
import scipy.constants
import pandas as pd
import numpy as np
import os
import json

try:
    from nmma.em.model import (
        SVDLightCurveModel,
        GRBLightCurveModel,
        SupernovaLightCurveModel,
        ShockCoolingLightCurveModel,
        SimpleKilonovaLightCurveModel,
        GenericCombineLightCurveModel,
    )
except ImportError as e:
    warnings.warn(
        f"Could not import EM models from nmma: {e}. Some features may not work."
    )

try:
    from nmma.em.io import loadEvent
except ImportError as e:
    warnings.warn(
        f"Could not import I/O utilities from nmma: {e}. Some features may not work."
    )

try:
    from nmma.em.utils import getFilteredMag
except ImportError as e:
    warnings.warn(
        f"Could not import utility functions from nmma: {e}. Some features may not work."
    )


def create_light_curve_model_from_args(
    model_name_arg,
    sample_times,
    svd_path,
    interpolation_type,
    filters=None,
    sample_over_Hubble=False,
    grb_resolution=7,
    jet_type=0,
    local_only=False,
):

    # Define parameter conversion function for Hubble sampling
    def parameter_conversion(converted_parameters, added_keys=[]):
        if "luminosity_distance" not in converted_parameters:
            Hubble_constant = converted_parameters["Hubble_constant"]
            redshift = converted_parameters["redshift"]
            # Calculate luminosity distance
            distance = redshift / Hubble_constant * scipy.constants.c / 1e3  # in Mpc
            converted_parameters["luminosity_distance"] = distance
            added_keys.append("luminosity_distance")
        return converted_parameters, added_keys

    # If not sampling over Hubble, set parameter_conversion to None
    if not sample_over_Hubble:
        parameter_conversion = None

    models = []
    model_names = (
        model_name_arg.split(",") if "," in model_name_arg else [model_name_arg]
    )

    for model_name in model_names:
        if model_name == "TrPi2018":
            # Initialize GRB light curve model
            lc_model = GRBLightCurveModel(
                sample_times=sample_times,
                resolution=grb_resolution,
                jetType=jet_type,
                parameter_conversion=parameter_conversion,
                filters=filters,
            )
        elif model_name in ["nugent-hyper", "salt2", "salt3"]:
            # Initialize Supernova light curve models
            lc_model = SupernovaLightCurveModel(
                sample_times=sample_times,
                model=model_name,  # Use the model_name directly as the model parameter
                parameter_conversion=parameter_conversion,
                filters=filters,
            )
        elif model_name == "Piro2021":
            # Initialize Shock Cooling light curve model
            lc_model = ShockCoolingLightCurveModel(
                sample_times=sample_times,
                parameter_conversion=parameter_conversion,
                filters=filters,
            )
        elif model_name in ["Me2017", "PL_BB_fixedT"]:
            # Initialize Simple Kilonova light curve model
            lc_model = SimpleKilonovaLightCurveModel(
                sample_times=sample_times,
                model=model_name,  # Use the model_name directly as the model parameter
                parameter_conversion=parameter_conversion,
                filters=filters,
            )
        elif model_name == "Sr2023":
            lc_model = HostGalaxyLightCurveModel(
                sample_times=sample_times,
                parameter_conversion=parameter_conversion,
                filters=filters,
            )
        else:
            # Initialize SVD light curve model for other model names
            lc_model = SVDLightCurveModel(
                model=model_name,
                sample_times=sample_times,
                svd_path=svd_path,
                mag_ncoeff=10,
                lbol_ncoeff=10,
                interpolation_type=interpolation_type,
                parameter_conversion=parameter_conversion,
                filters=filters,
                local_only=local_only,
            )
        models.append(lc_model)

    # Combine models if there are multiple, otherwise, use the single model
    light_curve_model = (
        models[0]
        if len(models) == 1
        else GenericCombineLightCurveModel(models, sample_times)
    )

    return model_names, models, light_curve_model


def get_bestfit_lightcurve(
    posterior_file,
    model,
    sample_times,
    svd_path,
    interpolation_type,
    filters_to_analyze,
    sample_over_Hubble=False,
    grb_resolution=7,
    jet_type=0,
    local_only=False,
    bestfit=False,
    error_budget=1,
    remove_nondetections=False,
    outdir=None,
    label=None,
):
    """
    Reads the best-fit light curve model parameters from a posterior file and generates the corresponding light curve.

    Parameters:
        posterior_file (str): Path to the file containing posterior samples.
        model (str): Name of the light curve model to use.
        sample_times (array): Array of times at which to sample the light curve.
        svd_path (str): Path to the directory containing SVD model data.
        interpolation_type (str): Type of interpolation to use.
        filters_to_analyze (list): List of filters to apply to the light curve.
        sample_over_Hubble (bool): Whether to sample over Hubble constant and redshift.
        grb_resolution (int): Resolution parameter for GRB models.
        jet_type (int): Type of jet model to use for GRB light curves.
        local_only (bool): Whether to only use locally available models and skip fetching from remote sources.
        bestfit (bool): Whether to save best-fit parameters to a file.
        error_budget (float): Error budget to use when generating the light curve.
        remove_nondetections (bool): Whether to remove non-detections from the analysis.
        outdir (str): Directory to save output files if bestfit is True.
        label (str): Label to use for output files if bestfit is True.

    Returns:
        tuple: A tuple containing the best-fit parameters, best-fit light curve magnitudes, model names, model instances, and the combined light curve model.
    """
    # Generate light curve model using provided parameters
    model_names, models, light_curve_model = create_light_curve_model_from_args(
        model_name_arg=model,
        sample_times=sample_times,
        svd_path=svd_path,
        interpolation_type=interpolation_type,
        filters=filters_to_analyze,
        sample_over_Hubble=sample_over_Hubble,
        grb_resolution=grb_resolution,
        jet_type=jet_type,
        local_only=local_only,
    )

    # Read posterior samples from the file
    posterior_samples = pd.read_csv(posterior_file, header=0, delimiter=" ")
    bestfit_idx = posterior_samples["log_likelihood"].idxmax()
    bestfit_params = posterior_samples.iloc[bestfit_idx].to_dict()

    # Print best-fit parameters
    print(f"Best fit parameters: {bestfit_params}\nBest fit index: {bestfit_idx}")

    # Generate the light curve based on the best-fit parameters
    # Note: generate_lightcurve is a placeholder function and needs to be implemented according to your light curve model.
    _, mag = light_curve_model.generate_lightcurve(sample_times, bestfit_params)
    for filt in mag.keys():
        if (
            "luminosity_distance" in bestfit_params
            and bestfit_params["luminosity_distance"] > 0
        ):
            mag[filt] += 5.0 * np.log10(
                bestfit_params["luminosity_distance"] * 1e6 / 10.0
            )  # Convert to apparent magnitudes

    # Adjust times if a time shift is included in the best-fit parameters
    if "timeshift" in bestfit_params:
        mag["bestfit_sample_times"] = [
            t + bestfit_params["timeshift"] for t in sample_times
        ]

    # Convert dictionary of magnitudes to a DataFrame for easier handling
    bestfit_lightcurve_mag = pd.DataFrame.from_dict(mag)

    # Save best-fit parameters and magnitudes to a JSON file if requested
    if bestfit and outdir and label:
        bestfit_file_path = os.path.join(outdir, f"{label}_bestfit_params.json")
        with open(bestfit_file_path, "w") as f:
            json.dump(
                {
                    "Best fit index": int(bestfit_idx),
                    "Best fit parameters": bestfit_params,
                    # Convert NumPy arrays to lists for JSON serialization
                    "Magnitudes": {
                        filt: mag[filt].tolist()
                        if hasattr(mag[filt], "tolist")
                        else mag[filt]
                        for filt in mag.keys()
                    },
                },
                f,
                indent=4,
            )
        print(f"Saved bestfit parameters and magnitudes to {bestfit_file_path}")

    return (
        bestfit_params,
        bestfit_lightcurve_mag,
        model_names,
        models,
        light_curve_model,
    )
