
import yaml

from conan.api.output import ConanOutput
from conan.errors import ConanException

def parse_list_from_args(args):
    out = ConanOutput()

    recipes_to_export = []
    if args.list:
        out.verbose(f"Parsing recipes from list {args.list}")
        with open(args.list, "r") as stream:
            try:
                recipes_to_export = yaml.safe_load(stream)['recipes']
            except yaml.YAMLError as exc:
                print(exc)
    elif args.name:
        recipes_to_export = [args.name]
    else:
        raise ConanException("Must specify at least -n or -l args for this to work")

    assert isinstance(recipes_to_export, list), "The code expects this to be an array"

    return recipes_to_export
