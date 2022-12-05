import os
import json
import yaml

# conan config install .conan
# conan cci:create-top-version fmt

from conan.api.output import ConanOutput
from conan.cli.command import conan_command


def output_json(exported):
    return json.dumps({"exported": [repr(r) for r in exported]})


@conan_command(group="Conan Center Index", formatters={"json": output_json})
def create_top_versions(conan_api, parser, *args):
    """
    Create top version for each folder
    """
    parser.add_argument("name")
    args = parser.parse_args(*args)
    result = []

    recipe_folder = os.path.join("recipes", args.name)
    if not os.path.isdir(recipe_folder):
        ConanOutput.error("ABORTING -- Make sure to run from CCI root")

    latest_folder_version = {}

    config_file = os.path.join(recipe_folder, "config.yml")
    if os.path.isfile(config_file):
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            for version in config["versions"]:
                folder = config["versions"][version]["folder"]
                if not folder in latest_folder_version:
                    latest_folder_version[folder] = version
    for folder, version in latest_folder_version.items():
        conanfile = os.path.join(recipe_folder, folder, "conanfile.py")
        conan_api.out.verbose(msg=f"Creating package for {args.name}/{version} from {folder}")

    return result
