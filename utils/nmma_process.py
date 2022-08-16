from astropy.time import Time
from astropy.table import Table
from astropy.io import ascii


def skyportal_input_to_nmma(data_dict):

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
    # the utils.py  file need jd format which will be convert in isot.

    rez = {"status": "failure", "message": "", "analysis": {}}

    try:

        data = Table.read(data_dict, format="ascii.csv")

        # convert time in julien day format (jd)
        # check if time is really in mjd format
        # if data["mjd"] is in mjd, time < 0

        for time_format in ["mjd", "jd"]:
            if (time_format == "mjd") & (time_format in data.columns):
                try:
                    time = Time(data["mjd"][0], format="jd").mjd

                except KeyError:
                    print(f" Sorry the name: {time_format} does not exits")

                else:
                    if time < 0:
                        data["mjd"] = Time(data["mjd"], format="mjd").jd

                data.rename_column("mjd", "jd")

            # check if the time is in  jd format
            # if data["jd"] is in jd, time < 0
            elif (time_format == "jd") & (time_format in data.columns):
                try:
                    time = Time(data["jd"][0], format="jd").mjd
                except KeyError:
                    print(f" Sorry the name: {time_format} does not exits")

                else:
                    if time < 0:
                        data["jd"] = Time(data["jd"], format="mjd").jd

        # Rename Columns from skyportal to nmma format
        # skyportal_col = ["magerr", "limiting_mag", "instrument_name"]

        for col in data.columns:
            if col == "magerr":
                data.rename_column("magerr", "mag_unc")

            elif col == "limmiting_mag":
                data.rename_column("limiting_mag", "limmag")

            elif col == "instrument_name":
                data.rename_column("instrument_name", "programid")

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

        if "obj_id" in data.columns:
            cand_name = data["obj_id"]

        else:
            cand_name = "ztf_filename"

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
