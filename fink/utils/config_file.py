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


def skyportal_admin_token(skyportal_token_path: str):

    """Read the new skyportal token in a dict
        in the yaml config file.
    Args:
        skyportal_token_path (str): Give the path where is the skyportal admin token.
        admin_token (.tokens.yaml): is the name of the skyportal admin token

    Returns: skyportal admin token
    """
    token = yaml_to_dict(skyportal_token_path)
    skyportal_token = token["INITIAL_ADMIN"]

    return skyportal_token


def update_config_file(config_file_path: str, skyportal_token_path: str):

    """
    Args:
        skyportal_path (str): Give the path where is the skyportal admin token.
        admin_token (.tokens.yaml): is the name of the skyportal admin token
        config_file_path(str): Give the config.yaml file dir

    Returns: skyportal admin token
    """
    try:
        conf = yaml_to_dict(config_file_path)

        conf["skyportal_token"] = skyportal_admin_token(skyportal_token_path)

        dict_to_yaml(conf, config_file_path)

    except Exception as exc:
        print(exc)
        print("Failed to copy skyportal token")
