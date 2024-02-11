from astropy.time import Time
from astropy.table import Table
import numpy as np


def skyportal_input_to_nmma(analysis_parameters):
    """
    Transforms photometry input data from SkyPortal format to the format expected by NMMA.

    This function checks the time column to ensure it's in the correct format. If the column is labeled
    as 'mjd' but the values are in JD format, it makes no changes. If the values are indeed in MJD format,
    it converts them to JD. It also renames certain columns to match NMMA's expected format and
    converts filter names if necessary.

    Parameters:
        data_dict (dict): A dictionary containing the path to the photometry CSV file.

    Returns:
        astropy.table.Table: The transformed data table ready for NMMA analysis.
    """

    # Initialize response structure
    rez = {"status": "failure", "message": "", "analysis": {}}

    try:
        # Read the CSV data into an Astropy Table
        datapath = analysis_parameters.get("photometry")
        data = Table.read(datapath, format="ascii.csv")

        # Loop to find and convert the time column
        time_column = None
        for time_column in ["mjd", "jd"]:
            if time_column in data.columns:
                # Directly check the original values without conversion
                original_values = data[time_column]

                # If any value is above the threshold, it's likely already in JD
                if np.any(original_values > 2400000.5):
                    print(f"Column '{time_column}' seems to be in JD format.")
                else:
                    print(
                        f"Column '{time_column}' seems to be in MJD format, converting to JD."
                    )
                    # Convert MJD to JD
                    data[time_column] = Time(original_values, format="mjd").jd

                # Ensure the time column is labeled 'jd'
                if time_column != "jd":
                    data.rename_column(time_column, "jd")

                break  # Exit the loop after handling the time column

        if time_column is None:
            raise ValueError("Time column (mjd or jd) not found in the input data.")

        # Rename columns to match NMMA format
        rename_map = {
            "magerr": "mag_unc",
            "limiting_mag": "limmag",
            "instrument_name": "programid",  # Assuming 'instrument_name' maps to 'programid'
        }
        for old_col, new_col in rename_map.items():
            if old_col in data.columns:
                data.rename_column(old_col, new_col)

        # Convert filter names to a standard format, if necessary
        # This example uses a simple conversion for ZTF filters as an illustration
        filter_conversion = {"g": "ztfg", "r": "ztfr", "i": "ztfi"}
        if "filter" in data.columns:
            data["filter"] = [
                filter_conversion.get(filt, filt) for filt in data["filter"]
            ]

        # Convert numerical filter codes to string values
        switcher = {1: "ztfg", 2: "ztfr", 3: "ztfi"}
        for i in range(len(data)):
            # Check if the filter value for the current row is one of the keys in the 'switcher' dictionary
            if data["filter"][i] in switcher:
                # Replace the numerical code with its corresponding string value
                data["filter"][i] = switcher[data["filter"][i]]

        # Fill missing data and sort by JD
        data = data.filled()
        data.sort("jd")

    except Exception as e:
        # Update response with error information
        rez.update(
            {
                "status": "failure",
                "message": f"Input data is not in the expected format: {e}",
            }
        )
        return rez

    # Return the transformed data table
    return data


def parse_csv(infile):
    """
    Reads photometric data from a CSV file and transforms it into a specific format.

    Parameters:
        infile (str): Path to the CSV file containing photometric data.

    Returns:
        list: A list of lists, where each sublist contains the transformed data for one observation.
    """

    # Read the CSV file using numpy.genfromtxt, skipping the first line (header)
    in_data = np.genfromtxt(
        infile, dtype=None, delimiter=",", skip_header=1, encoding=None
    )

    out_data = []
    for line in in_data:
        # Convert JD time to ISO format using astropy.time.Time
        time_iso = Time(line[1], format="jd").isot

        # Handle non-detections where mag is 99.0 by using limit_mag and setting error to infinity
        mag = line[5] if line[2] == 99.0 else line[2]
        error = np.inf if line[2] == 99.0 else line[3]

        # Append the transformed data to out_data
        out_data.append([time_iso, str(line[4]), str(mag), str(error)])

    return out_data
