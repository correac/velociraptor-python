"""
Main objects for holding information relating to the autoplotter.
"""

from velociraptor import VelociraptorCatalogue
from velociraptor.autoplotter.lines import VelociraptorLine
from velociraptor.exceptions import AutoPlotterError
import velociraptor.autoplotter.plot as plot

from unyt import unyt_quantity, unyt_array
from numpy import log10, linspace, logspace
from matplotlib.pyplot import Axes, Figure
from yaml import safe_load
from typing import Union, List, Dict, Tuple

from os import path, mkdir
from functools import reduce

valid_plot_types = ["scatter", "2dhistogram", "massfunction"]
valid_line_types = ["median", "mean"]


class VelociraptorPlot(object):
    """
    Object representing a single figure of x against y.
    """

    # Forward declarations
    # What type of plot are we?
    plot_type: str
    # variable to plot on the x-axis
    x: str
    # variable to plot on the y-axis
    y: str
    # log the x/y axes?
    x_log: bool
    y_log: bool
    # Units for x/y
    x_units: unyt_quantity
    y_units: unyt_quantity
    # Plot limits for x/y
    x_lim: List[Union[unyt_quantity, None]]
    y_lim: List[Union[unyt_quantity, None]]
    # override the axes?
    x_label_override: Union[None, str]
    y_label_override: Union[None, str]
    # plot median/mean line and give it properties
    mean_line: Union[None, VelociraptorLine]
    median_line: Union[None, VelociraptorLine]
    # Binning for x, y axes.
    number_of_bins: int
    x_bins: unyt_array
    y_bins: unyt_array

    def __init__(self, filename: str, data: Dict[str, Union[Dict, str]]):
        """
        Initialise the plot object variables.
        """
        self.filename = filename
        self.data = data

        self._parse_data()

        return

    def _parse_coordinate_quantity(self, coordinate: str) -> None:
        """
        Parses x or y to self.{x,y} and self.{x,y}_units.
        """
        try:
            setattr(self, coordinate, self.data[coordinate]["quantity"])
            setattr(
                self,
                f"{coordinate}_units",
                unyt_quantity(1.0, units=self.data[coordinate]["units"]),
            )
        except KeyError:
            raise AutoPlotterError(
                f"You must provide an {coordinate}-quantity and units to plot for {self.filename}"
            )

        return

    def _set_coordinate_quantity_none(self, coordinate: str) -> None:
        """
        Sets a coordinates quantity and units to None and (dimensionless)
        respectively. Useful for e.g. mass functions or histograms.
        """

        setattr(self, coordinate, None)
        setattr(self, f"{coordinate}_units", unyt_quantity(1.0, units=None))

        return

    def _parse_coordinate_limit(self, coordinate: str) -> None:
        """
        Parses the x or y limit to {x,y}_limit.
        """
        setattr(self, f"{coordinate}_lim", [None, None])

        try:
            getattr(self, f"{coordinate}_lim")[0] = unyt_quantity(
                float(self.data[coordinate]["start"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

        try:
            getattr(self, f"{coordinate}_lim")[1] = unyt_quantity(
                float(self.data[coordinate]["end"]),
                units=self.data[coordinate]["units"],
            )
        except KeyError:
            pass

        return

    def _parse_coordinate_log(self, coordinate: str) -> None:
        """
        Parses x_log from the parameter file data.
        """

        try:
            setattr(self, f"{coordinate}_log", bool(self.data[coordinate]["log"]))
        except KeyError:
            setattr(self, f"{coordinate}_log", True)

        return

    def _parse_coordinate_label_override(self, coordinate: str) -> None:
        """
        Parses {x,y}_label_override.
        """

        try:
            setattr(
                self,
                f"{coordinate}_label_override",
                self.data[coordinate]["label_override"],
            )
        except KeyError:
            setattr(self, f"{coordinate}_label_override", None)

        return

    def _parse_line(self, line_type: str) -> None:
        """
        Parses a line type to {line_type}_line.
        """

        try:
            setattr(
                self,
                f"{line_type}_line",
                VelociraptorLine(line_type, self.data[line_type]),
            )
        except KeyError:
            setattr(self, f"{line_type}_line", None)

        return

    def _parse_lines(self) -> None:
        """
        Parses all lines to VelociraptorLine objects using _parse_line individually.
        """

        for line_type in valid_line_types:
            self._parse_line(line_type)

        return

    def _parse_number_of_bins(self) -> None:
        """
        Parses the number of bins.
        """

        try:
            self.number_of_bins = int(self.data["number_of_bins"])
        except KeyError:
            self.number_of_bins = 128

        return

    def _parse_coordinate_histogram_bin(self, coordinate: str) -> None:
        """
        Parses the histogram bins for a given histogram axis, given by
        co-ordinate. Specifically x:start and x:end.
        """

        start, end = getattr(self, f"{coordinate}_lim")

        if getattr(self, f"{coordinate}_log"):
            # Need to strip units, unfortunately
            setattr(
                self,
                f"{coordinate}_bins",
                unyt_array(
                    logspace(log10(start), log10(end), self.number_of_bins),
                    units=start.units,
                ),
            )
        else:
            # Can get away with this one without stripping
            setattr(
                self, f"{coordinate}_bins", linspace(start, end, self.number_of_bins)
            )

        return

    def _parse_scatter(self) -> None:
        """
        Parses the required variables for producing a scatter plot.
        """

        for coordinate in ["x", "y"]:
            self._parse_coordinate_quantity(coordinate)
            self._parse_coordinate_log(coordinate)
            self._parse_coordinate_limit(coordinate)
            self._parse_coordinate_label_override(coordinate)

        self._parse_lines()

        return

    def _parse_2dhistogram(self) -> None:
        """
        Parses the required variables for producing a background
        2d histogram plot.
        """

        # Requires everything for the scatter, but with extra tacked
        # on.

        self._parse_scatter()
        self._parse_number_of_bins()

        for coordinate in ["x", "y"]:
            self._parse_coordinate_histogram_bin(coordinate)

        return

    def _parse_massfunction(self) -> None:
        """
        Parses the required variables for producing a mass function
        plot.
        """

        self._parse_coordinate_quantity("x")
        self._set_coordinate_quantity_none("y")

        for coordinate in ["x", "y"]:
            self._parse_coordinate_log(coordinate)
            self._parse_coordinate_limit(coordinate)
            self._parse_coordinate_label_override(coordinate)

        self._parse_number_of_bins()
        self._parse_coordinate_histogram_bin("x")

        return

    def _parse_histogram(self) -> None:
        """
        Parses the required variables for producing a 1D histogram plot.
        """

        # Same as mass function, unsurprisingly!
        self._parse_massfunction()

        return

    def _parse_data(self):
        """
        Federates out data parsing to individual functions based on the
        plot type.
        """

        try:
            self.plot_type = self.data["type"]
        except KeyError:
            self.plot_type = "scatter"

        if self.plot_type not in valid_plot_types:
            raise AutoPlotterError(
                f"Plot type {self.plot_type} is not valid. Please choose from {valid_plot_types}."
            )

        getattr(self, f"_parse_{self.plot_type}")()

        return

    def _add_lines_to_axes(self, ax: Axes, x: unyt_array, y: unyt_array) -> None:
        """
        Adds any lines present to the given axes.
        """

        if self.median_line is not None:
            self.median_line.plot_line(ax=ax, x=x, y=y, label="Median")
        if self.mean_line is not None:
            self.mean_line.plot_line(ax=ax, x=x, y=y, label="Mean")

        return

    def _make_plot_scatter(
        self, catalogue: VelociraptorCatalogue
    ) -> Tuple[Figure, Axes]:
        """
        Makes a scatter plot and returns the figure and axes.
        """

        x = reduce(getattr, self.x.split("."), catalogue)
        x.convert_to_units(self.x_units)
        y = reduce(getattr, self.y.split("."), catalogue)
        y.convert_to_units(self.y_units)

        fig, ax = plot.scatter_x_against_y(x, y)

        if self.x_log:
            ax.set_xscale("log")
        if self.y_log:
            ax.set_yscale("log")

        ax.set_xlim(*self.x_lim)
        ax.set_ylim(*self.y_lim)

        self._add_lines_to_axes(ax=ax, x=x, y=y)

        return fig, ax

    def _make_plot_2dhistogram(
        self, catalogue: VelociraptorCatalogue
    ) -> Tuple[Figure, Axes]:
        """
        Makes a 2d histogram plot and returns the figure and axes.
        """

        x = reduce(getattr, self.x.split("."), catalogue)
        x.convert_to_units(self.x_units)
        y = reduce(getattr, self.y.split("."), catalogue)
        y.convert_to_units(self.y_units)

        self.x_bins.convert_to_units(self.x_units)
        self.y_bins.convert_to_units(self.y_units)

        fig, ax = plot.histogram_x_against_y(x, y, self.x_bins, self.y_bins)

        if self.x_log:
            ax.set_xscale("log")
        if self.y_log:
            ax.set_yscale("log")

        ax.set_xlim(*self.x_lim)
        ax.set_ylim(*self.y_lim)

        self._add_lines_to_axes(ax=ax, x=x, y=y)

        return fig, ax

    def _make_plot_massfunction(
        self, catalogue: VelociraptorCatalogue
    ) -> Tuple[Figure, Axes]:
        """
        Makes a mass function plot and returns the figure and axes.
        """

        x = reduce(getattr, self.x.split("."), catalogue)
        x.convert_to_units(self.x_units)

        self.x_bins.convert_to_units(self.x_units)

        fig, ax = plot.mass_function(
            x,
            self.x_bins,
            box_volume=catalogue.units.box_volume / (catalogue.units.a ** 3),
        )

        if self.x_log:
            ax.set_xscale("log")
        if self.y_log:
            ax.set_yscale("log")

        ax.set_xlim(*self.x_lim)
        ax.set_ylim(*self.y_lim)

        return fig, ax

    def make_plot(
        self, catalogue: VelociraptorCatalogue, directory: str, file_extension: str
    ):
        """
        Federates out data parsing to individual functions based on the
        plot type.
        """

        fig, ax = getattr(self, f"_make_plot_{self.plot_type}")(catalogue=catalogue)

        plot.decorate_axes(ax=ax, catalogue=catalogue)

        fig.tight_layout()
        fig.savefig(f"{directory}/{self.filename}.{file_extension}")

        return


class AutoPlotter(object):
    """
    Main autoplotter object; contains all of the VelociraptorPlot objects
    and parsing code to turn the input yaml file into those.
    """

    # Forward declarations
    catalogue: VelociraptorCatalogue
    yaml: Dict[str, Union[Dict, str]]
    plots: List[VelociraptorPlot]

    def __init__(self, filename: str) -> None:
        """
        Initialises the AutoPlotter object with the yaml filename.
        """

        self.filename = filename
        self.load_yaml()
        self.parse_yaml()

        return

    def load_yaml(self):
        """
        Loads the yaml data from file.
        """

        with open(self.filename, "r") as handle:
            self.yaml = safe_load(handle)

        return

    def parse_yaml(self):
        """
        Parse the contents of the given yaml file into a list of
        VelociraptorPlot instances (self.plots).
        """

        self.plots = [
            VelociraptorPlot(filename, plot) for filename, plot in self.yaml.items()
        ]

        return

    def link_catalogue(self, catalogue: VelociraptorCatalogue):
        """
        Links a catalogue with this object so that the plots
        can actually be created.
        """

        self.catalogue = catalogue

        return

    def create_plots(self, directory: str, file_extension: str = "pdf"):
        """
        Creates and saves the plots in a directory.
        """

        # Try to create the directory
        if not path.exists(directory):
            mkdir(directory)

        for plot in self.plots:
            plot.make_plot(
                catalogue=self.catalogue,
                directory=directory,
                file_extension=file_extension,
            )

        return
