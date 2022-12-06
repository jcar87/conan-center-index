import os
import json
import yaml

# conan config install .conan
# conan cci:create-top-versions fmt

from conan.api.output import ConanOutput
from conan.cli.args import add_profiles_args
from conan.cli.command import conan_command, OnceArgument
from conan.cli.printers.graph import print_graph_basic, print_graph_packages
from conan.errors import ConanException


# is this the correct API?
from conans.model.recipe_ref import RecipeReference


def output_json(exported):
    return json.dumps({"exported": [repr(r) for r in exported]})

@conan_command(group="Conan Center Index", formatters={"json": output_json})
def create_top_versions(conan_api, parser, *args):
    """
    Build the "top" version from each recipe folder
    """
    parser.add_argument('-n', '--name', action=OnceArgument, help="Name of the recipe to export")
    parser.add_argument('-l', '--list', action=OnceArgument, help="YAML file with list of recipes to export")
    add_profiles_args(parser)
    args = parser.parse_args(*args)

    out = ConanOutput()

    recipes_to_create = []
    if args.list:
        out.verbose(f"Parsing recipes from list {args.list}")
        with open(args.list, "r") as stream:
            try:
                recipes_to_create = yaml.safe_load(stream)['recipes']
            except yaml.YAMLError as exc:
                out.error(exc)
                raise ConanException("Failed to parse list of recipe")
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
        out.title(recipe_name)

        config_file = os.path.join("recipes", recipe_name, "config.yml")
        if not os.path.exists(config_file):
            out.error(f"The file {config_file} does not exist")
            return created, failed

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
            print_graph_basic(deps_graph)
            if deps_graph.error:
                out.writeln(f"{reference} - error computing dependency graph")
                failed.add((reference, deps_graph.error))
                continue

            try:
                conan_api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=[], update=False,
                                        lockfile=None)
                print_graph_packages(deps_graph)
            except Exception as e:
                out.writeln(f"Something failed with {reference}: {str(e)}")
                failed.add((reference, str(e)))
                continue

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

    return created, failed

