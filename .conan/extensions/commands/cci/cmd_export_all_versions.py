import os
import json
import textwrap
import yaml

# conan config install .conan
# conan cci:export-all-versions -n fmt

from conan.api.output import ConanOutput
from conan.cli.command import conan_command, OnceArgument
from conan.errors import ConanException

from .cci_list_or_name import parse_list_from_args

def output_json(results):
    print(json.dumps({
        "exported": [repr(r) for r in results["exported"]],
        "failures": [f for f in results["failures"]]
    }))

def output_markdown(results):
    failures = results["failures"]
    print(textwrap.dedent(f"""
    ### Conan Export Results

    Successfully exported {len(results["exported"])} versions while encountering {len(failures)} recipes that could not be exported; these are


    <table>
    <th>
    <td> Recipe </td> <td> Reason </td>
    </th>"""))

    for key, value in failures.items():
        print(textwrap.dedent(f"""
            <tr>
            <td> {key} </td>
            <td>

            ```txt
            """))
        print(f"{value}")
        print(textwrap.dedent(f"""
            ```

            </td>
            </tr>
            """))

    print("</table>")


@conan_command(group="Conan Center Index", formatters={"json": output_json, "md": output_markdown})
def export_all_versions(conan_api, parser, *args):
    """
    Export all version for a recipe
    """
    parser.add_argument('-n', '--name', action=OnceArgument, help="Name of the recipe to export")
    parser.add_argument('-l', '--list', action=OnceArgument, help="YAML file with list of recipes to export")
    args = parser.parse_args(*args)

    recipes_to_export = parse_list_from_args(args)

    out = ConanOutput()

    # Result output variables, these should always be returned
    exported = []
    failed = dict()

    for item in recipes_to_export:
        recipe_name = item if not isinstance(item, dict) else list(item.keys())[0]
        out.verbose(f"Starting recipe '{recipe_name}'")

        recipe_folder = os.path.join("recipes", recipe_name)
        if not os.path.isdir(recipe_folder):
            raise ConanException(f"Invalid user input: '{recipe_name}' folder does not exist")

        config_file = os.path.join(recipe_folder, "config.yml")
        if not os.path.isfile(config_file):
            raise ConanException(f"The file {config_file} does not exist")

        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            for version in config["versions"]:
                recipe_subfolder = config["versions"][version]["folder"]
                conanfile = os.path.join(recipe_folder, recipe_subfolder, "conanfile.py")
                if not os.path.isfile(conanfile):
                    raise ConanException(f"The file {conanfile} does not exist")

                out.verbose(f"Exporting {recipe_name}/{version} from {recipe_subfolder}/")
                try:
                    ref = conan_api.export.export(os.path.abspath(conanfile), recipe_name, version, None, None)
                    out.verbose(f"Exported {ref}")
                    exported.append(ref)
                except Exception as e:
                    failed.update({f"{recipe_name}/{recipe_subfolder}": str(e)})

    out.title("EXPORTED RECIPES")
    for item in exported:
        out.info(f"{item[0]}")

    out.title("FAILED TO EXPORT")
    for item in failed.items():
        out.info(f"{item[0]}")

    return {"exported": exported, "failures": failed}
