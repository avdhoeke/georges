import numpy as np
import numpy.linalg as npl
import pandas as pd

from georges.sequence_geometry import compute_derived_data


class BeamlineException(Exception):
    """Exception raised for errors in the Beamline module."""

    def __init__(self, m):
        self.message = m


class Beamline:
    """A beamline or accelerator model.

    The internal representation is essentially a pandas DataFrames.
    """

    def __init__(self, beamline, name=None, from_survey=False, with_expansion=True, start=None, stop=None):
        """
        :param beamline: defines the beamline to be created. It can be
            - a single pandas Dataframe
            - a list that can be used to create a DataFrame
            - another beamline ('copy' operation)
        :param name: the name of the beamline to be created
        :param from_survey: indicates (True/False) is the beamline is to be converted from survey data
        """

        # Default values
        self.__length = 0
        self.__name = name
        self.__beamline = None
        self.__start = start
        self.__stop = stop
        self.__from_survey = from_survey

        # Process the beamline argument
        self.__create(beamline)

        # Verify that the beamline was created correctly
        if self.__beamline is None:
            raise BeamlineException("No beamline defined.")

        # Converts from survey data
        if self.__from_survey:
            self.__convert_angles_to_radians()
            self.__expand_sequence_data()
            self.__convert_survey_to_sequence()

        # Compute derived data until a fixed point sequence is reached
        if with_expansion:
            self.__expand_sequence_data()

        # Compute the sequence length
        if self.__length == 0 and self.__beamline.get('AT_EXIT') is not None:
            self.__length = self.__beamline.get('AT_EXIT').max()

        # Beamline must be defined
        assert self.__length is not None
        assert self.__beamline is not None

    def __create(self, beamline):
        """Process the arguments of the initializer."""
        # Some type inference to get the sequence right
        # Sequence from a pandas.DataFrame
        if isinstance(beamline, pd.DataFrame):
            if 'NAME' in beamline.columns:
                self.__beamline = beamline.set_index('NAME') if beamline.index.names[0] is not 'NAME' else beamline
            else:
                self.__beamline = beamline
            if self.__name is None:
                self.__name = getattr(beamline, 'name', 'BEAMLINE')
            else:
                self.__beamline.name = self.__name
            if self.__beamline.size == 0:
                raise BeamlineException("Empty dataframe.")
            self.__beamline.index.name = 'NAME'
        # Sequence from a list
        # Assume that a DataFrame can be created from the list
        if isinstance(beamline, list):
            self.__create(pd.DataFrame(beamline))
        # Sequence from another Beamline
        if isinstance(beamline, Beamline):
            self.__create(beamline.line)

    def __expand_sequence_data(self):
        """Apply sequence transformation until a fixed point is reached."""
        tmp = self.__beamline.apply(compute_derived_data, axis=1)
        tmp2 = tmp
        while True:
            tmp, tmp2 = tmp2, tmp.apply(compute_derived_data, axis=1)
            if tmp.equals(tmp2):
                break
        self.__beamline = tmp2

    def __convert_survey_to_sequence(self):
        s = self.__beamline
        if 'LENGTH' not in s:
            s['LENGTH'] = np.nan
        offset = s['ORBIT_LENGTH'][0] / 2.0
        if pd.isnull(offset):
            offset = 0
        self.__beamline['AT_CENTER'] = pd.DataFrame(
            npl.norm(
                [
                    s['X'].diff().fillna(0.0),
                    s['Y'].diff().fillna(0.0)
                ],
                axis=0
            ) - (
                s['LENGTH'].fillna(0.0) / 2.0 - s['ORBIT_LENGTH'].fillna(0.0) / 2.0
            ) + (
                s['LENGTH'].shift(1).fillna(0.0) / 2.0 - s['ORBIT_LENGTH'].shift(1).fillna(0.0) / 2.0
            )).cumsum() / 1000.0 + offset
        self.__converted_from_survey = True

    def __convert_angles_to_radians(self):
        # Angle conversion
        if 'ANGLE' in self.__beamline:
            self.__beamline['ANGLE'] *= np.pi / 180.0
        if 'ANGLE_ELEMENT' in self.__beamline:
            self.__beamline['ANGLE_ELEMENT'] *= np.pi / 180.0

    @property
    def name(self):
        """The sequence name."""
        return self.__name

    @property
    def length(self):
        """The sequence length."""
        return self.__length

    def add_extra_drift(self, extra):
        """Increase the sequence length by adding a drift"""
        self.__length += extra

    @property
    def line(self):
        """The beamline representation."""
        self.__beamline.name = self.name
        self.__beamline.length = self.length
        if self.__start is None and self.__stop is None:
            tmp = self.__beamline
        else:
            tmp = self.__beamline[self.__start:self.__stop].copy()
        tmp[['AT_ENTRY', 'AT_CENTER', 'AT_EXIT']] -= tmp.iloc[0]['AT_ENTRY']
        tmp.name = self.name
        tmp.length = tmp.iloc[-1]['AT_EXIT']
        return tmp

    def to_thin(self, element):
        """Useful for MAD-X tracking"""
        bl = self.__beamline
        bl.at[element, 'LENGTH'] = 0.0
        bl.at[element, 'ORBIT_LENGTH'] = 0.0
        bl.at[element, 'AT_ENTRY'] = bl.loc[element]['AT_CENTER']
        bl.at[element, 'AT_EXIT'] = bl.loc[element]['AT_CENTER']
        bl.at[element, 'CLASS'] = 'QUADRUPOLE'
        bl.at[element, 'APERTYPE'] = np.nan
        bl.at[element, 'APERTURE'] = np.nan

    def add_markers(self):
        s = self.__beamline
        markers = []

        def create_marker(r):
            if r['CLASS'] != 'MARKER' and r['CLASS'] != 'INSTRUMENT' and r['CLASS'] != 'DRIFT':
                if r.name + '_IN' in s.index and r.name + '_OUT' in s.index:
                    return r
                m = pd.Series({
                    'TYPE': 'MARKER',
                    'CLASS': 'MARKER',
                    'NAME': r.name + '_IN',
                    'AT_CENTER': r['AT_ENTRY'],
                    'PHYSICAL': False
                })
                markers.append(m)
                m = pd.Series({
                    'TYPE': 'MARKER',
                    'CLASS': 'MARKER',
                    'NAME': r.name + '_OUT',
                    'AT_CENTER': r['AT_EXIT'],
                    'PHYSICAL': False
                })
                markers.append(m)
            return r

        s.apply(create_marker, axis=1)
        if len(markers) == 0:
            return self
        else:
            return Beamline(
                pd.concat([
                    s,
                    pd.DataFrame(markers).set_index('NAME')
                ]).sort_values(by='AT_CENTER'),
                name=self.name,
                start=self.__start,
                stop=self.__stop
            )

    def add_drifts(self, using_collimators=False, with_pipe=True, pipe_aperture=1.0, pipe_apertype='CIRCLE'):
        line_with_drifts = pd.DataFrame()
        at_entry = 0

        def create_drift(name, length, at, apertype=None, aperture=None):
            class_type = 'DRIFT' if not using_collimators else 'COLLIMATOR'
            pipe = True if using_collimators or with_pipe else False
            s = pd.Series(
                {
                    'CLASS': class_type,
                    'TYPE': class_type,
                    'PIPE': pipe,
                    'LENGTH': length,
                    'AT_ENTRY': at,
                    'AT_CENTER': at + length / 2.0,
                    'AT_EXIT': at + length,
                    'APERTYPE': apertype,
                    'APERTURE': aperture,
                    'PHYSICAL': False,
                }
            )
            s.name = name
            return s

        for r in self.__beamline.iterrows():
            i = r[0]
            e = r[1]
            diff = e['AT_ENTRY'] - at_entry
            if diff <= 1e-6:
                line_with_drifts = line_with_drifts.append(e)
            else:
                line_with_drifts = line_with_drifts.append(
                    create_drift(
                        name=f"DRIFT_{i}",
                        length=diff,
                        at=at_entry,
                        apertype=pipe_apertype,
                        aperture=pipe_aperture,
                    )).append(e)
            at_entry = e['AT_EXIT']

        negative_drifts = line_with_drifts.query("LENGTH < 0.0")
        if len(negative_drifts.index) > 0:
            raise BeamlineException(f"Negative drift detected for elements {negative_drifts.index.values}.")
        return Beamline(line_with_drifts, name=self.name, start=self.__start, stop=self.__stop)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Beamline(self, start=key.start, stop=key.stop)
        else:
            return self

    def __setitem__(self, key, value):
        self.__beamline.at[key] = value

    @staticmethod
    def from_concatenation(beamlines):
        offset = 0
        names = []
        bl = []
        for b in beamlines:
            tmp = b.line.copy()
            names.append(b.name)
            bl.append(tmp)
            tmp['AT_ENTRY'] += offset
            tmp['AT_CENTER'] += offset
            tmp['AT_EXIT'] += offset
            offset += b.length
        return Beamline(bl, name='_'.join(names), with_expansion=False)
