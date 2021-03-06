from typing import Dict
import pandas as pd
from . import manzoni
from .common import _process_model_argument
from .observers import Observer
from .. import Beamline
from .. import Beam


class TrackException(Exception):
    """Exception raised for errors in the Track module."""

    def __init__(self, m: str):
        self.message = m


def track(model=None, line: Beamline = None, beam: Beam = None, context: Dict = {}, **kwargs) -> Beamline:
    """
    Compute the distribution of the beam as it propagates through the beamline.

    :param model:
    :param line:
    :param beam:
    :param context:
    :param kwargs:
    :return:
    """
    # Process arguments
    v = _process_model_argument(model, line, beam, context, TrackException)

    # Run Manzoni
    o = Observer(elements=list(range(len(v['manzoni_line']))))
    manzoni.track(line=v['manzoni_line'], beam=v['manzoni_beam'], observer=o, **kwargs)

    # Collect the results
    return Beamline(
        v['georges_line'].line.reset_index().merge(
            pd.DataFrame(
                list(
                    map(
                        lambda x: Beam(
                            pd.DataFrame(x)
                        ),
                        o.data[0, :]
                    )
                ),
                columns=['BEAM']
            ),
            left_index=True,
            right_index=True,
            how='left'
        ).set_index('NAME'))
