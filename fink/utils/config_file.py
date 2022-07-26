# coding: utf-8
# ---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :
#  @email          :
#  @repo           :
#  @createdOn      :
#  @description    : Read skyportal-fink-client a yaml configuration file
# ---------------------------------------------------------------------------
import os
import yaml


def load_config(datapath: str, config_file: str = "config.yaml"):
    """
    Open and  Converts a yaml configuration file to a dictionary.
    :param datapath(str): The path to the yaml file.
    :return: A dictionary.
    """
    with open(f"{datapath}{config_file}", "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return config


def dump_config(dict_file: dict, datapath: str, config_file: str = "config.yaml"):

    """Converts a dictionary to a yaml file.
    :param dict_file(dict): The dictionary to be converted.
    :param datapath(str): the path where the yaml file is to be saved.
    :return: Nothing.
    Save the yaml config file in the datapath directory.
    """
    with open(f"{datapath}{config_file}", "w") as stream:
        try:
            yaml.dump(dict_file, stream)
        except yaml.YAMLError as exc:
            print(exc)


def get_skyportal_admin_token(datapath: str, admin_token: str = ".tokens.yaml"):

    """Read the new skyportal token in a dict
        in the yaml config file.
    Args:
        skyportal_token_path (str): Give the path where is the skyportal admin token.
        admin_token (.tokens.yaml) (str): is the name of the skyportal admin token

    Returns: skyportal admin token
    """
    token = load_config(datapath, admin_token)

    return token["INITIAL_ADMIN"]


def update_config_file(
    config_path: str, config_file, skyportal_token_path, admin_token
):

    """
    Args:
        skyportal_path (str): Give the path where is the skyportal admin token.
        admin_token (.tokens.yaml): is the name of the skyportal admin token
        config_file_path(str): Give the config.yaml file dir

    Returns: skyportal admin token
    """
    try:
        config = load_config(config_path, config_file)
        config["skyportal_token"] = get_skyportal_admin_token(
            skyportal_token_path, admin_token
        )
        config["fink_topics"] = config["fink_topics"]
        dump_config(config, config_path, config_file)

    except Exception as exc:
        print(exc)
        print("Failed to copy skyportal token")
