import numpy as np
from .constants import *


class IntegratorException(Exception):
    """Exception raised for errors in the Track module."""

    def __init__(self, m):
        self.message = m


def _drift(l):
    """
    Transfer matrix of a drift.
    :param l: drift length
    :return: a numpy array representing the 5D transfer matrix
    """
    return np.array(
        [
            [1, l, 0, 0, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 1, l, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 0, 1]
        ]
    )


def sextupole(e, b, **kwargs):
    b[:, 1] = e[INDEX_K2] * (b[:, X]**2 - b[:, Y]**2)
    b[:, 3] = e[INDEX_K2] * (b[:, X] * b[:, Y])
    return b


def octupole(e, b, **kwargs):
    b[:, 1] = e[INDEX_K3] * (b[:, X]**3 - 3 * b[:, X] * b[:, Y]**2)
    b[:, 3] = e[INDEX_K3] * (3 * b[:, X]**2 * b[:, Y] - b[:, Y]**3)
    return b


def decapole(e, b, **kwargs):
    b[:, 1] = e[INDEX_K3] * (b[:, X]**4 - 6 * b[:, X]**2 * b[:, Y]**2 + b[:, Y]**4)
    b[:, 3] = e[INDEX_K3] * (b[:, X]**3 * b[:, Y] - b[:, X] * b[:, Y]**3)
    return b


def multipole(e, b, **kwargs):
    return np.array(
        [
            0,
            0,
            0,
            0,
            0
        ]
    )


def hkicker(e, b, order=1, nst=1, **kwargs):
    if order == 1:
        return _hkicker1(e, b, nst, **kwargs)
    elif order == 2:
        return _hkicker2(e, b, nst, **kwargs)
    elif order == 4:
        return _hkicker4(e, b, nst, **kwargs)
    else:
        raise IntegratorException("Invalid integrator order.")


def _hkicker1(e, b, nst=1, **kwargs):
    if e[INDEX_LENGTH] <= 1e-6:
        nst = 1
    drift = _drift(e[INDEX_LENGTH] / nst)
    k = e[INDEX_KICK] / nst
    for i in range(0, nst):
        b = b.dot(drift.T)
        b[:, PX] += k
    return b


def _hkicker2(e, b, nst=1, **kwargs):
    if e[INDEX_LENGTH] <= 1e-6:
        nst = 1
    drift = _drift(e[INDEX_LENGTH] / nst / 2.0)
    k = e[INDEX_KICK] / nst
    for i in range(0, nst):
        b = b.dot(drift.T)
        b[:, PX] += k
        b = b.dot(drift.T)
    return b


def _hkicker4(e, b, nst=1, **kwargs):
    if e[INDEX_LENGTH] <= 1e-6:
        nst = 1
    drift = _drift(e[INDEX_LENGTH] / nst / 2.0)
    k = e[INDEX_KICK] / nst
    for i in range(0, nst):
        b = b.dot(drift.T)
        b[:, PX] += k
        b = b.dot(drift.T)
    return b


def vkicker(e, b, nst=1, **kwargs):
    if e[INDEX_LENGTH] <= 1e-6:
        nst = 1
    drift = _drift(e[INDEX_LENGTH] / nst)
    k = e[INDEX_KICK] / nst
    for i in range(0, nst):
        b = b.dot(drift.T)
        b[:, PY] += k
    return b


integrators = {
    CLASS_CODES['SEXTUPOLE']: sextupole,
    CLASS_CODES['OCTUPOLE']: octupole,
    CLASS_CODES['DECAPOLE']: decapole,
    CLASS_CODES['MULTIPOLE']: multipole,
    CLASS_CODES['HKICKER']: hkicker,
    CLASS_CODES['VKICKER']: vkicker,
}
