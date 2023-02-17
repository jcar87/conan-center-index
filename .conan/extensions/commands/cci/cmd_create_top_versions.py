import os
import json
import textwrap
import yaml

# conan config install .conan
# conan cci:create-top-versions -n fmt

from conan.api.output import ConanOutput
from conan.cli.args import add_profiles_args
from conan.cli.command import conan_command, OnceArgument
from conan.cli.commands.test import run_test
from conan.cli.printers.graph import print_graph_packages
from conan.errors import ConanException, ConanInvalidConfiguration

from conan.tools.scm import Version
# is this the correct API?
from conans.model.recipe_ref import RecipeReference

from .cci_list_or_name import parse_list_from_args

def output_json(results):    print(json.dumps({
        "created": [repr(r) for r in results["created"]],
        "failures": [f for f in results["failures"]]
    }))

def output_markdown(results):
    failures = results["failures"]
    print(textwrap.dedent(f"""
    ### Conan Build and Test Results

    Successfully built {len(results["created"])} packages while encountering {len(failures)} recipes that could not be built; these are


    <table>
    <th>
    <td> Package </td> <td> Reason </td>
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
def create_top_versions(conan_api, parser, *args):
    """
    Build the "top" version from each recipe folder
    """
    parser.add_argument('-n', '--name', action=OnceArgument, help="Name of the recipe to export")
    parser.add_argument('-l', '--list', action=OnceArgument, help="YAML file with list of recipes to export")
    add_profiles_args(parser)
    args = parser.parse_args(*args)

    recipes_to_create = parse_list_from_args(args)

    out = ConanOutput()

    created = {}
    failed = {}

    profile_host, profile_build = conan_api.profiles.get_profiles_from_args(args)
    out.title("Input profiles")
    out.info("Profile host:")
    out.info(profile_host.dumps())
    out.info("Profile build:")
    out.info(profile_build.dumps())

    for item in recipes_to_create:
        recipe_name = item if not isinstance(item, dict) else list(item.keys())[0]
        folders_to_build = item[recipe_name][0]['folders'] if isinstance(item, dict) else None
        out.verbose(f"Beginning to look into {recipe_name}")

        config_file = os.path.join("recipes", recipe_name, "config.yml")
        if not os.path.exists(config_file):
            raise ConanException(f"The file {config_file} does not exist")

        # Add the upper most version for each new recipe folder we have.
        known_versions = {}
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)

            for version, folder in config["versions"].items():
                folder_name = folder['folder']
                if folders_to_build and folder_name not in folders_to_build:
                    continue
                if not folder_name in known_versions or Version(version) > Version(known_versions[folder_name]):
                    known_versions.update({folder_name: version})

        # Since we will "conan install --build=missing --requires"
        # We dont need to go to each recipe folder and do a build
        # This is assuming the "export all command" was run before hand
        for folder_name, version_to_build in known_versions.items():
            reference = f"{recipe_name}/{version_to_build}"
            out.title(reference)
            in_cache = False if not conan_api.search.recipes(reference, remote=None) else True # None remote is "local cache"
            if not in_cache:
                out.warning(f"{reference} was not found in the cache and will be skipped")
                failed.update({reference: "Not in cache - probably fails to export"})
                continue

            try:
                deps_graph = conan_api.graph.load_graph_requires(requires=[reference], tool_requires=[],
                    profile_host=profile_host, profile_build=profile_build, lockfile=None, remotes=[],
                    update=False, check_updates=False)
                conan_api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=[], update=False,
                                        lockfile=None)
                print_graph_packages(deps_graph)
            except Exception as e:
                out.error(f"{reference} load graph failed with: {str(e)}")
                failed.update({reference: str(e)})
                continue

            try:
                conan_api.install.install_binaries(deps_graph=deps_graph, remotes=[])
                created.update({reference: False})
            except ConanInvalidConfiguration:
                out.warning(f"Invalid configuration for {reference}, skipping")
                created.update({reference: False})
                continue
            except Exception as e:
                out.error(f"{reference} build failed with: {str(e)}")
                failed.update({reference: str(e)})
                continue

            try:
                test_package_folder = os.path.join(os.getcwd(), "recipes", recipe_name, folder_name, "test_package", "conanfile.py")
                run_test(conan_api, test_package_folder, RecipeReference.loads(reference), profile_host, profile_build, remotes=[], lockfile=None, update=False, build_modes=['missing'])
                created.update({reference: True})
            except Exception as e:
                out.error(f"{reference} test package failed with: {str(e)}")
                del created[reference]
                failed.update({reference: f"Package succeeded build, but failed during test_package with error:\n{str(e)}"})
                continue

            # TODO: probably want to show the entire reference (rrev and prev)

    out.title("Built recipes")
    for reference, test_package in created.items():
        test_package_text = "" if test_package else "(! failed test pacakge)"
        out.info(f"{reference} {test_package_text}")

    out.title("Failed to build")
    for item in failed:
        out.info(f"{item}")

    return {"created": created, "failures": failed}

