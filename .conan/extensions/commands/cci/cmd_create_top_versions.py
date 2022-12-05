import os
import json
import yaml

# conan config install .conan
# conan cci:create-top-version fmt

from conan.api.output import ConanOutput
from conan.cli.command import conan_command
from conan.cli.printers.graph import print_graph_basic, print_graph_packages


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

    out = ConanOutput()

    recipe_folder = os.path.join("recipes", args.name)
    if not os.path.isdir(recipe_folder):
        out.error("ABORTING -- Make sure to run from CCI root")

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
        conanfile_path = os.path.join(recipe_folder, folder, "conanfile.py")
        cwd = os.getcwd()
        path = conan_api.local.get_conanfile_path(conanfile_path, cwd, py=True)

        out.verbose(f"Creating package for {args.name}/{version} from {folder}")
        ref = conan_api.export.export(path, args.name, version, None, None)

        profile_host = conan_api.profiles.get_profile(
            [conan_api.profiles.get_default_host()]
        )
        profile_build = conan_api.profiles.get_profile(
            [conan_api.profiles.get_default_build()]
        )

        out.title("Input profiles")
        out.info("Profile host:")
        out.info(profile_host.dumps())
        out.info("Profile build:")
        out.info(profile_build.dumps())

        out.verbose(f"Loading root graph from {path}")
        root_node = conan_api.graph.load_root_consumer_conanfile(
            path,
            profile_host,
            profile_build,
            name=args.name,
            version=version,
            user=None,
            channel=None,
            lockfile=None,  # ???
            remotes=None,  # ???
            update=False,
        )

        out.title("Computing dependency graph")
        deps_graph = conan_api.graph.load_graph(
            root_node,
            profile_host=profile_host,
            profile_build=profile_build,
            lockfile=None,
            remotes=None,
            update=False,
            check_update=False,
        )
        print_graph_basic(deps_graph)

        out.title("Computing necessary packages")
        build_modes = ["*"]
        conan_api.graph.analyze_binaries(
            deps_graph, build_modes, lockfile=None, remotes=None, update=False
        )
        print_graph_packages(deps_graph)

        out.title("Installing packages")
        conan_api.install.install_binaries(
            deps_graph=deps_graph, remotes=None, update=False
        )

        result.append(ref)

    return result
