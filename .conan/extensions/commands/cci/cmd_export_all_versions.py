import os
import json
import textwrap
import yaml

# conan config install .conan
# conan cci:export-all-versions fmt

from conan.api.output import ConanOutput
from conan.cli.command import conan_command, OnceArgument

def output_json(results):
    print(json.dumps({
        "exported": [repr(r) for r in results["exported"]],
        "failures": [f for f in results["failures"]]
    }))

def output_markdown(results):
    failures = results["failures"]
    print(textwrap.dedent(f"""
    ### Conan Export Results

    Successfully exported {len(results["exported"])} versions while encountering {len(failures)} recipes that could not be exported; there are


    <table>
    <th>
    <td> Recipe </td> <td> Reason </td>
    </th>"""))

    for item in failures:
        # print(f"{item[0]} | ```{item[1]}```".replace("\n", " "))
        print(textwrap.dedent(f"""
            <tr>
            <td> {item[0]} </td>
            <td>

            ```txt
            """))
        print(f"{item[1]}")
        print(textwrap.dedent(f"""
            ```

            </td>
            </tr>
            </table>
            """))

    print("")


@conan_command(group="Conan Center Index", formatters={"json": output_json, "md": output_markdown})
def export_all_versions(conan_api, parser, *args):
    """
    Export all version for a recipe
    """
    parser.add_argument('-n', '--name')
    parser.add_argument('-l', '--list', action=OnceArgument, help="YAML file with list of recipes to export")
    args = parser.parse_args(*args)

    out = ConanOutput()

    recipes_to_export = []
    if args.list:
        out.verbose(f"Parsing recipes from list {args.list}")
        with open(args.list, "r") as stream:
            try:
                recipes_to_export = yaml.safe_load(stream)['recipes']
            except yaml.YAMLError as exc:
                print(exc)
    else:
        recipes_to_export = args.name

    exported = []
    failed = set()

    for item in recipes_to_export:
        recipe_name = item if not isinstance(item, dict) else list(item.keys())[0]
        folders = None if not isinstance(item, dict) else item[recipe_name][0]['folders']

        recipe_folder = os.path.join("recipes", recipe_name)
        if not os.path.isdir(recipe_folder):
            out.error(f"ABORTING - {recipe_name}'s folder does not exist")
            return exported, failed

        config_file = os.path.join(recipe_folder, "config.yml")

        if not os.path.exists(config_file):
            out.error(f"ABORTING: file {config_file} does not exist")
            return exported, failed

        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            for version in config["versions"]:
                recipe_subfolder = config["versions"][version]["folder"]
                if folders and not  recipe_subfolder in folders:
                    continue

                conanfile = os.path.join(recipe_folder, recipe_subfolder, "conanfile.py")
                out.verbose(f"Conanfile to export: {conanfile}")
                if os.path.isfile(conanfile):
                    out.verbose(f"Exporting {recipe_name}/{version}")
                    try:
                        ref = conan_api.export.export(os.path.abspath(conanfile), recipe_name, version, None, None)
                        out.verbose(f"Exported {ref}")
                        exported.append(ref)
                    except Exception as e:
                        failed.add((f"{recipe_name}/{recipe_subfolder}", str(e)))

    out.title("EXPORTED RECIPES")
    for item in exported:
        out.info(f"{item[0]}")

    out.title("FAILED TO EXPORT")
    for item in failed:
        out.info(f"{item[0]}")

    return {"exported": exported, "failures": failed}
