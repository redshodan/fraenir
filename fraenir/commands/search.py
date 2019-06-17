from . import registerCmd


@registerCmd
class Search:
    NAME = "search"
    KWARGS = {"help": "Search recorded messages"}

    def __call__(self, args):
        return "Search.__call__"
