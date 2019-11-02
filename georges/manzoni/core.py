from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import numpy as _np
if TYPE_CHECKING:
    from .input import Input as _Input
    from .beam import Beam as _Beam
    from .observers import Observer as _Observer


def track(beamline: _Input,
          beam: _Beam,
          observer: Optional[_Observer] = None,
          check_apertures: bool = True
          ):
    """

    Args:
        beamline:
        beam:
        observer:
        check_apertures:

    Returns:

    """
    global_parameters = [
        beam.kinematics.beta
    ]
    b1 = _np.copy(beam.distribution)
    b2 = _np.zeros(b1.shape)
    for e in beamline.sequence:
        b1, b2 = e.propagate(b1, b2, global_parameters)
        if check_apertures:
            b1, b2 = e.check_aperture(b1, b2)
            if observer is not None:
                observer(e, b1, b2)
        b2, b1 = b1, b2


def match(beamline: _Input,
          beam: _Beam,):
    pass
