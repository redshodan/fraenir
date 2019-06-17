from . import registerCmd


@registerCmd
class Fermi:
    NAME = "fermi"
    KWARGS = {"help": "Define yet another solution to the Fermi Paradox"}

    def __call__(self, args):
        return "Fermi.__call__"
