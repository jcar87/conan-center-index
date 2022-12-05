import os
import json
import yaml

# conan config install .conan
# conan cci:export-all-versions fmt

from conan.api.output import ConanOutput
from conan.cli.command import conan_command

def output_json(exported):
    return json.dumps({"exported": [repr(r) for r in exported]})


@conan_command(group="Conan Center Index", formatters={"json": output_json})
def export_all_versions(conan_api, parser, *args):
    """
    Exporting several recipes
    """
    parser.add_argument('name')
    args = parser.parse_args(*args)
    result = []

    recipefolder = os.path.join("recipes", args.name)
    if not os.path.isdir(recipefolder):
      print("ABORTING -- Make sure to run from CCI root")

    configfile = os.path.join(recipefolder, "config.yml")
    if os.path.isfile(configfile):
       with open(configfile, "r") as file:
          config = yaml.safe_load(file)
          for version in config["versions"]:
            conanfile = os.path.join(recipefolder, config["versions"][version]["folder"], "conanfile.py")
            if os.path.isfile(conanfile):
                print("Exporting", args.name, version)
                ref = conan_api.export.export(os.path.abspath(conanfile), args.name, version, None, None)
                result.append(ref)
    return result
