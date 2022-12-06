import os
import json
import yaml

# conan config install .conan
# conan cci:create-top-versions fmt

from conan.api.output import ConanOutput
from conan.cli.args import add_profiles_args
from conan.cli.command import conan_command, OnceArgument
from conan.cli.printers.graph import print_graph_basic, print_graph_packages


# is this the correct API?
from conans.model.recipe_ref import RecipeReference


def output_json(exported):
    return json.dumps({"exported": [repr(r) for r in exported]})

@conan_command(group="Conan Center Index", formatters={"json": output_json})
def create_top_versions(conan_api, parser, *args):
    """
    Export all version for a recipe
    """
    parser.add_argument('-n', '--name')
    parser.add_argument('-l', '--list', action=OnceArgument, help="YAML file with list of recipes to export")
    add_profiles_args(parser)
    args = parser.parse_args(*args)

    result = []

    out = ConanOutput()
    out.writeln(args)

    recipes_to_create = []

    if args.list:
        out.writeln(f"Parsing recipes from list {args.list}")
        with open(args.list, "r") as stream:
            try:
                recipes_to_create = yaml.safe_load(stream)['recipes']
            except yaml.YAMLError as exc:
                print(exc)
    else:
        recipes_to_create = args.name

    created = []
    failed = set()

    profile_host, profile_build = conan_api.profiles.get_profiles_from_args(args)
    out.title("Input profiles")
    out.info("Profile host:")
    out.info(profile_host.dumps())
    out.info("Profile build:")
    out.info(profile_build.dumps())

    for item in recipes_to_create:

        recipe_name = item if not isinstance(item, dict) else list(item.keys())[0]
        folders = None if not isinstance(item, dict) else item[recipe_name][0]['folders']

        recipe_folder = os.path.join("recipes", recipe_name)

        if not os.path.isdir(recipe_folder):
            out.error("ABORTING - Path does not exist")

        config_file = os.path.join(recipe_folder, "config.yml")

        if not os.path.exists(config_file):
            out.error(f"ABORTING: file {config_file} does not exist")

        with open(config_file, "r") as file:
            config = yaml.safe_load(file)

            all_versions = config["versions"]

            # Assume that the version to build is the first in the list,
            # this may not be right
            # TODO: ensure that we respect 'folders'
            version_to_build = list(all_versions.keys())[0]

            reference = f"{recipe_name}/{version_to_build}"
            out.title(reference)
            in_cache = False if not conan_api.search.recipes(reference, remote=None) else True # None remote is "local cache"
            if not in_cache:
                failed.add((reference, "Not in cache - fails to export"))
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

            out.writeln(deps_graph)
            print_graph_basic(deps_graph)
            if deps_graph.error:
                out.writeln(f"{reference} - error computing dependency graph")

            conan_api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=[], update=False,
                                     lockfile=None)
            print_graph_packages(deps_graph)

            try:
                conan_api.install.install_binaries(deps_graph=deps_graph, remotes=[], update=False)
                created.append(reference)
            except Exception as e: 
                out.writeln(f"Something failed with {reference}: {str(e)}")
                failed.add((reference, str(e)))


             # TODO: probably want to show the entire reference (rrev and prev)


    out.title("--------- BUILT RECIPES ---------")
    for item in created:
        out.writeln(item)

    out.title("--------- FAILED TO BUILD ---------")
    for item in failed:
        out.writeln(f"{item[0]}, reason: {item[1]}")

    return result

