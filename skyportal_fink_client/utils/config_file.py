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


def yaml_to_dict(datapath: str):
    """
    Open and  Converts a yaml configuration file to a dictionary.
    :param datapath(str): The path to the yaml file.
    :param config_filename(str): the config filname
    :return: A dictionary.
    """
    with open(datapath, "r") as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return conf


def dict_to_yaml(dict: dict, datapath: str):

    """Converts a dictionary to a yaml file.
    :param dict(dict): The dictionary to be converted.
    :param datapath(str): the path where the yaml file is to be saved.
    :return: Nothing.
    Save the yaml config file in the datapath directory.
    """
    with open(datapath, "w") as stream:
        try:
            yaml.dump(dict, stream)
        except yaml.YAMLError as exc:
            print(exc)


def skyportal_admin_token(skyportal_path: str, admin_token: str = ".tokens.yaml"):

    """Read the new skyportal token in a dict
        in the yaml config file.
    Args:
        skyportal_path (str): Give the path where is the skyportal admin token.
        admin_token (str='.tokens.yaml'): is the name of the skyportal admin token
        config_filename(str): the config file name

    Returns: skyportal admin token
    """
    token_path = f"{skyportal_path}{admin_token}".format()
    skyportal_token = yaml_to_dict(token_path)
    skyportal_token = skyportal_token["INITIAL_ADMIN"]
    assert skyportal_token is not None
    assert skyportal_token is not ""

    return skyportal_token
