import os
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from nmma.em.utils import getFilteredMag

matplotlib.rcParams.update(
    {"font.size": 16, "text.usetex": True, "font.family": "Times New Roman"}
)


def check_and_remove_non_detection(data_out, remove_nondetections=False):
    """
    Check and optionally remove non-detection data from photometric observations.

    Parameters:
    - data_out: A dictionary with filter names as keys and data arrays as values.
    - remove_nondetections (bool): If True, removes non-detection data points.

    Returns:
    - The updated data_out dictionary with non-detections optionally removed.
    """

    if remove_nondetections:
        # Iterate over each filter in the data
        filters_to_check = list(data_out.keys())
        for filt in filters_to_check:
            # Find indices of data points where the magnitude error is finite
            idx = np.where(np.isfinite(data_out[filt][:, 2]))[0]
            # Update the data for the current filter with only the valid detections
            data_out[filt] = data_out[filt][idx, :]
            # If all data points were non-detections (i.e., idx is empty), remove the filter from the data
            if len(idx) == 0:
                del data_out[filt]

    # Check if there's at least one valid detection in the data
    detection = False
    notallnan = False
    for filt in data_out.keys():
        # Check if there's at least one finite magnitude value (detection)
        idx = np.where(np.isfinite(data_out[filt][:, 2]))[0]
        if len(idx) > 0:
            detection = True
        # Check if there's at least one finite magnitude error value
        idx = np.where(np.isfinite(data_out[filt][:, 1]))[0]
        if len(idx) > 0:
            notallnan = True
        # If there's at least one detection with a finite error, no need to check further
        if detection and notallnan:
            break

    # If there are no valid detections or all magnitude errors are NaN, raise an error
    if not detection or not notallnan:
        raise ValueError("Need at least one detection to do fitting.")

    return data_out


def plot_bestfit_lightcurve(
    data_out,
    trigger_time,
    filters_to_analyze,
    error_budget,
    plotName,
    bestfit_params,
    bestfit_lightcurve_mag,
    model_names,
    models,
    light_curve_model,
):

    mag = bestfit_lightcurve_mag

    if len(models) > 1:
        _, mag_all = light_curve_model.generate_lightcurve(
            plot_sample_times, bestfit_params, return_all=True
        )

        for ii in range(len(mag_all)):
            for filt in mag_all[ii].keys():
                if bestfit_params["luminosity_distance"] > 0:
                    mag_all[ii][filt] += 5.0 * np.log10(
                        bestfit_params["luminosity_distance"] * 1e6 / 10.0
                    )
        model_colors = cm.Spectral(np.linspace(0, 1, len(models)))[::-1]

    filters_plot = []
    for filt in filters_to_analyze:
        if filt not in data_out:
            continue
        samples = data_out[filt]
        t, y, sigma_y = samples[:, 0], samples[:, 1], samples[:, 2]
        idx = np.where(~np.isnan(y))[0]
        t, y, sigma_y = t[idx], y[idx], sigma_y[idx]
        if len(t) == 0:
            continue
        filters_plot.append(filt)

    colors = cm.Spectral(np.linspace(0, 1, len(filters_plot)))[::-1]

    plt.figure(figsize=(20, 16))
    color2 = "coral"

    cnt = 0
    for filt, color in zip(filters_plot, colors):
        cnt = cnt + 1
        if cnt == 1:
            ax1 = plt.subplot(len(filters_plot), 1, cnt)
        else:
            ax2 = plt.subplot(len(filters_plot), 1, cnt, sharex=ax1, sharey=ax1)

        samples = data_out[filt]
        t, y, sigma_y = samples[:, 0], samples[:, 1], samples[:, 2]
        t -= trigger_time
        idx = np.where(~np.isnan(y))[0]
        t, y, sigma_y = t[idx], y[idx], sigma_y[idx]

        idx = np.where(np.isfinite(sigma_y))[0]
        plt.errorbar(
            t[idx],
            y[idx],
            sigma_y[idx],
            fmt="o",
            color="k",
            markersize=16,
        )  # or color=color

        idx = np.where(~np.isfinite(sigma_y))[0]
        plt.errorbar(
            t[idx], y[idx], sigma_y[idx], fmt="v", color="k", markersize=16
        )  # or color=color

        mag_plot = getFilteredMag(mag, filt)

        plt.plot(
            mag["bestfit_sample_times"],
            mag_plot,
            color=color2,
            linewidth=3,
            linestyle="--",
        )

        if len(models) > 1:
            plt.fill_between(
                mag["bestfit_sample_times"],
                mag_plot + error_budget[filt],
                mag_plot - error_budget[filt],
                facecolor=color2,
                alpha=0.2,
                label="Combined",
            )
        else:
            plt.fill_between(
                mag["bestfit_sample_times"],
                mag_plot + error_budget[filt],
                mag_plot - error_budget[filt],
                facecolor=color2,
                alpha=0.2,
            )

        if len(models) > 1:
            for ii in range(len(mag_all)):
                mag_plot = getFilteredMag(mag_all[ii], filt)
                plt.plot(
                    mag["bestfit_sample_times"],
                    mag_plot,
                    color=color2,
                    linewidth=3,
                    linestyle="--",
                )
                plt.fill_between(
                    mag["bestfit_sample_times"],
                    mag_plot + error_budget[filt],
                    mag_plot - error_budget[filt],
                    facecolor=model_colors[ii],
                    alpha=0.2,
                    label=models[ii].model,
                )

        plt.ylabel("%s" % filt, fontsize=48, rotation=0, labelpad=40)

        plt.xlim([float(x) for x in [0.0, 10.0]])
        plt.ylim([float(x) for x in [22.0, 14.0]])
        plt.grid()

        if cnt == 1:
            ax1.set_yticks([26, 22, 18, 14])
            plt.setp(ax1.get_xticklabels(), visible=False)
            if len(models) > 1:
                plt.legend(
                    loc="upper right",
                    prop={"size": 18},
                    numpoints=1,
                    shadow=True,
                    fancybox=True,
                )
        elif not cnt == len(filters_plot):
            plt.setp(ax2.get_xticklabels(), visible=False)
        plt.xticks(fontsize=36)
        plt.yticks(fontsize=36)

    ax1.set_zorder(1)
    plt.xlabel("Time [days]", fontsize=48)
    plt.tight_layout()
    plt.savefig(plotName)
    plt.close()
