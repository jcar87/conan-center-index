import json
import os
import yaml

import conan.api.conan_api
from conan.api.model import ListPattern
from conan.api.output import ConanOutput
from conan.cli.command import conan_command, OnceArgument
from conan.errors import ConanException


def output_json(results):
    print(json.dumps(results, indent=2))


@conan_command(group="Conan Center Index", formatters={"json": output_json})
def list_v2_ready(conan_api: conan.api.conan_api.ConanAPI, parser, *args):
    """
    Build the "top" version from each recipe folder
    """
    parser.add_argument('-n', '--name', action='append', default=list(), help="Only process this recipe")
    parser.add_argument('-r', '--remote', action=OnceArgument, help="Remote to query against")
    parser.add_argument('-p', '--profiles', action='append', default=list(), help="List of profiles to run graph info with")
    args = parser.parse_args(*args)

    recipes_to_create = args.name if args.name else os.listdir('./recipes/')
    remote = conan_api.remotes.get(args.remote)
    profiles = [(conan_api.profiles.get_profile([profile]), profile) for profile in args.profiles]

    out = ConanOutput()

    global_results = {}

    for recipe_name in recipes_to_create:
        recipe_results = {}
        global_results[recipe_name] = recipe_results
        recipe_folder = os.path.join("recipes", recipe_name)
        config_file = os.path.join(recipe_folder, "config.yml")
        if not os.path.exists(config_file):
            raise ConanException(f"The file {config_file} does not exist")

        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            for version in config["versions"]:
                version_results = {"exported": False, "latest_local_revision": None, "is_latest_local_revision_in_remote": None, "binary_status_per_profile": {}}
                recipe_results[version] = version_results
                ref = f"{recipe_name}/{version}"
                try:
                    recipe_subfolder = config["versions"][version]["folder"]
                    conanfile = os.path.join(recipe_folder, recipe_subfolder, "conanfile.py")
                    if not os.path.isfile(conanfile):
                        raise ConanException(f"The file {conanfile} does not exist")

                    out.info(f"Exporting {ref} from {recipe_subfolder}")
                    try:
                        rref, conanfile = conan_api.export.export(os.path.abspath(conanfile), recipe_name, version, None, None)
                        rev = f"{rref}#{rref.revision}"
                        out.success(f"Exported {rev}")
                        version_results["exported"] = True
                        version_results["latest_local_revision"] = rref.revision
                    except ConanException as e:
                        out.error(f"Error while exporting {ref}: {e}")
                        version_results["exported"] = False
                        continue

                    try:
                        out.info(f"Listing {rev} from {args.remote} remote")
                        ref_pattern = ListPattern(rev)
                        # This raises if rev is not in remote
                        selection = conan_api.list.select(ref_pattern, remote=remote)
                        out.success(f"conan list {rev} -r {args.remote}: {selection.serialize()}")
                        version_results["is_latest_local_revision_in_remote"] = True
                    except ConanException as e:
                        # The rev does not exist in the remote
                        out.error(f"Error while listing revs for {ref} in {args.remote}: {e}")\
                            .warning(f"{rev} does not exist in the remote")
                        version_results["is_latest_local_revision_in_remote"] = False
                        continue

                    out.info(f"Running graph info for {len(profiles)} profiles")
                    for profile_contents, profile_name in profiles:
                        try:
                            out.info(f"Loading graph for {rev} with {profile_name} profile")
                            deps_graph = conan_api.graph.load_graph_requires([rev], tool_requires=[], profile_host=profile_contents, profile_build=profile_contents,
                                                                             lockfile=None, remotes=[remote], update=False, allow_error=True, check_updates=False)
                            conan_api.graph.analyze_binaries(deps_graph, build_mode=None, remotes=[remote], update=False, lockfile=False)
                            serialized = deps_graph.serialize()
                            # Get the node for our recipe, raises if not found
                            recipe_node = next(filter(lambda node: node["ref"] == rev, serialized["nodes"]))
                            has_binaries = recipe_node["binary"] == "Download"
                            if has_binaries:
                                out.success(f"{rev} (profile {profile_name}) is in the remote and has binaries")
                                version_results["binary_status_per_profile"][profile_name] = "Present"
                            else:
                                out.error(f"{rev} (profile {profile_name}) is in the remote but has no binaries")
                                version_results["binary_status_per_profile"][profile_name] = "Missing"
                        except ConanException as e:
                            out.error(f"Error with graph info {ref}: {str(e)}")
                except Exception as e:
                    out.error(f"Unexpected error for {ref}: {e}")
    return global_results
