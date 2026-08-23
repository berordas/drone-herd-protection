"""Corre hashA con el wolf_controllers.py de HEAD (pre-refactor): se pre-importa desde el
override ANTES de importar hashA (que mete /workspace al frente), quedando cacheado en
sys.modules — todo lo demás sale de /workspace."""
import sys
sys.path.insert(0, "/data/hrl_e0/verif/pre_override")
import wolf_controllers                                  # noqa: E402  <- versión HEAD
assert "pre_override" in wolf_controllers.__file__, wolf_controllers.__file__
sys.path.insert(0, "/data/hrl_e0/verif")
import hashA                                             # noqa: E402
sys.argv = ["hashA.py", "pre"]
hashA.main()
