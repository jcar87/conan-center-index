import os
import json
import textwrap
import yaml

# conan config install .conan
# conan cci:create-top-versions -n fmt

from conan.api.output import ConanOutput
from conan.cli.args import add_profiles_args
from conan.cli.command import conan_command, OnceArgument
from conan.cli.printers.graph import print_graph_basic, print_graph_packages
from conan.errors import ConanException

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
    ### Conan Export Results

    Successfully build {len(results["created"])} packages while encountering {len(failures)} recipes that could not be built; these are


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

    created = []
    failed = dict()

    profile_host, profile_build = conan_api.profiles.get_profiles_from_args(args)
    out.title("Input profiles")
    out.info("Profile host:")
    out.info(profile_host.dumps())
    out.info("Profile build:")
    out.info(profile_build.dumps())

    for item in recipes_to_create:
        recipe_name = item if not isinstance(item, dict) else list(item.keys())[0]
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
                if not folder_name in known_versions:
                    known_versions.update({folder_name: version})

        # Since we will "conan install --build=missing --requires"
        # We dont need to go to each recipe folder and do a build
        # This is assuming the "export all command" was run before hand
        for _, version_to_build in known_versions.items():
            reference = f"{recipe_name}/{version_to_build}"
            out.title(reference)
            in_cache = False if not conan_api.search.recipes(reference, remote=None) else True # None remote is "local cache"
            if not in_cache:
                out.warning(f"{reference} was not found in the cache and will be skipped")
                failed.update({reference: "Not in cache - probably fails to export"})
                continue

            requires = [RecipeReference.loads(reference)]
            root_node = conan_api.graph.load_root_virtual_conanfile(requires=requires,
                                                                tool_requires=[],
                                                                profile_host=profile_host)

            deps_graph = conan_api.graph.load_graph(root_node, profile_host=profile_host,
                                            profile_build=profile_build,
                                            lockfile=None,
                                            remotes=[],
                                            update=False,
                                            check_update=False)
            print_graph_basic(deps_graph)
            if deps_graph.error:
                out.error(f"{reference} - error computing dependency graph")
                failed.update({reference: deps_graph.error})
                continue

            try:
                conan_api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=[], update=False,
                                        lockfile=None)
                print_graph_packages(deps_graph)
            except Exception as e:
                out.error(f"Something failed with: {str(e)}")
                failed.update({reference: str(e)})
                continue

            try:
                conan_api.install.install_binaries(deps_graph=deps_graph, remotes=[], update=False)
                created.append(reference)
            except Exception as e:
                out.error(f"Something failed with: {str(e)}")
                failed.update({reference: str(e)})

            # TODO: probably want to show the entire reference (rrev and prev)

    out.title("BUILT RECIPES")
    for item in created:
        out.info(item)

    out.title("FAILED TO BUILD")
    for item in failed:
        out.info(f"{item}")

    return {"created": created, "failures": failed}

