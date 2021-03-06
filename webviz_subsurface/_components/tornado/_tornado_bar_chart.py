from typing import Optional, List, Dict, Any

import pandas as pd
import plotly.graph_objects as go

from webviz_subsurface._abbreviations.number_formatting import si_prefixed
from webviz_subsurface._utils.formatting import printable_int_list
from ._tornado_data import TornadoData


class TornadoBarChart:
    """Creates a plotly bar figure from a TornadoData instance"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        tornado_data: TornadoData,
        plotly_theme: Dict[str, Any],
        figure_height: Optional[int] = None,
        label_options: str = "detailed",
        locked_si_prefix: Optional[int] = None,
        number_format: str = "",
        unit: str = "",
        spaced: bool = True,
        use_true_base: bool = False,
        show_realization_points: bool = True,
    ) -> None:
        self._tornadotable = tornado_data.tornadotable
        self._realtable = self.make_points(tornado_data.real_df)
        self._reference_average = tornado_data.reference_average
        self._plotly_theme = plotly_theme
        self._number_format = number_format
        self._unit = unit
        self._spaced = spaced
        self._locked_si_prefix = locked_si_prefix
        self._locked_si_prefix_relative: Optional[int]
        self._scale = tornado_data.scale
        self._use_true_base = use_true_base
        if self._scale == "Percentage":
            self._unit_x = "%"
            self._locked_si_prefix_relative = 0
        else:
            self._unit_x = self._unit
            self._locked_si_prefix_relative = locked_si_prefix
        self._figure_height = figure_height
        self._label_options = label_options
        self._show_scatter = show_realization_points

    def make_points(self, realdf: pd.DataFrame) -> pd.DataFrame:
        dfs = []
        for sensname in self._tornadotable["sensname"].unique():
            for case in ["high", "low"]:
                df = realdf.loc[
                    realdf["REAL"].isin(
                        self._tornadotable[self._tornadotable["sensname"] == sensname][
                            f"{case}_reals"
                        ].iloc[0]
                    )
                ].copy()
                df["sensname"] = sensname
                df["case"] = case
                dfs.append(df)
        return pd.concat(dfs)

    @property
    def figure_height(self) -> Optional[int]:
        """Set height of figure as a function of number of senscases(bars)"""
        return self._figure_height

    def _set_si_prefix(self, value: float) -> str:
        return str(
            si_prefixed(
                value,
                self._number_format,
                self._unit,
                self._spaced,
                self._locked_si_prefix,
            )
        )

    def _set_si_prefix_relative(self, value: float) -> str:
        return str(
            si_prefixed(
                value,
                self._number_format,
                self._unit_x,
                self._spaced,
                self._locked_si_prefix_relative,
            )
        )

    def bar_labels(self, case: str) -> List:

        if self._label_options == "simple":
            return [
                f"<b>{self._set_si_prefix_relative(x)}</b>, "
                for x in self._tornadotable[f"{case}_tooltip"]
            ]
        if self._label_options == "detailed":
            return [
                f"<b>{self._set_si_prefix_relative(x)}</b>, "
                f"True: {self._set_si_prefix(val)}, "
                f"<br><b>Case: {label}</b>, "
                f"Reals: {printable_int_list(reals)}"
                if reals
                else None
                for x, label, val, reals in zip(
                    self._tornadotable[f"{case}_tooltip"],
                    self._tornadotable[f"{case}_label"],
                    self._tornadotable[f"true_{case}"],
                    self._tornadotable[f"{case}_reals"],
                )
            ]
        return []

    @property
    def data(self) -> List:
        return [
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["low"],
                name="low",
                base=self._tornadotable["low_base"]
                if not self._use_true_base
                else self._reference_average,
                customdata=self._tornadotable["low_reals"],
                text=self.bar_labels("low"),
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="none",
                orientation="h",
                marker={"line": {"width": 1.5, "color": "black"}},
            ),
            dict(
                type="bar",
                y=self._tornadotable["sensname"],
                x=self._tornadotable["high"],
                name="high",
                base=self._tornadotable["high_base"]
                if not self._use_true_base
                else self._reference_average,
                customdata=self._tornadotable["high_reals"],
                text=self.bar_labels("high"),
                textposition="auto",
                insidetextanchor="middle",
                hoverinfo="none",
                orientation="h",
                marker={"line": {"width": 1.5, "color": "black"}},
            ),
        ]

    def calculate_scatter_value(self, case_values: pd.Series) -> List:
        if self._use_true_base:
            return case_values
        if self._scale == "Percentage":
            return (
                (case_values - self._reference_average) / self._reference_average
            ) * 100
        return case_values - self._reference_average

    @property
    def scatter_data(self) -> List[Dict]:
        return [
            {
                "type": "scatter",
                "mode": "markers",
                "y": df["sensname"],
                "x": self.calculate_scatter_value(df["VALUE"]),
                "text": df["REAL"],
                "hoverinfo": "none",
                "marker": {
                    "size": 15,
                    "color": self._plotly_theme["layout"]["colorway"][0]
                    if case == "low"
                    else self._plotly_theme["layout"]["colorway"][1],
                },
            }
            for case, df in self._realtable.groupby("case")
        ]

    @property
    def range(self) -> List[float]:
        """Calculate x-axis range so that the reference is centered"""
        max_val = max(self._tornadotable[["low", "high"]].abs().max())
        if self._use_true_base:
            return [
                (self._reference_average - max_val) * 0.95,
                (self._reference_average + max_val) * 1.05,
            ]
        return [-max_val * 1.05, max_val * 1.05]

    @property
    def layout(self) -> Dict:
        _layout: Dict[str, Any] = go.Layout()
        _layout.update(self._plotly_theme["layout"])
        _layout.update(
            {
                "height": self.figure_height,
                "barmode": "overlay",
                "margin": {"l": 0, "r": 0, "b": 20, "t": 0, "pad": 21},
                "xaxis": {
                    "title": self._scale,
                    "range": self.range,
                    "autorange": self._show_scatter,
                    "showgrid": False,
                    "zeroline": False,
                    "linecolor": "black",
                    "showline": True,
                    "automargin": True,
                    "side": "top",
                    "tickfont": {"size": 15},
                },
                "yaxis": {
                    "autorange": True,
                    "showgrid": False,
                    "zeroline": False,
                    "showline": False,
                    "automargin": True,
                    "title": None,
                    "dtick": 1,
                    "tickfont": {"size": 15},
                },
                "showlegend": False,
                "hovermode": "y",
                "annotations": [
                    {
                        "x": 0 if not self._use_true_base else self._reference_average,
                        "y": 1.05,
                        "xref": "x",
                        "yref": "paper",
                        "text": f"<b>{self._set_si_prefix(self._reference_average)}</b>"
                        " (Ref avg)",
                        "showarrow": False,
                        "align": "center",
                    }
                ],
                "shapes": [
                    {
                        "type": "line",
                        "line": {"width": 3, "color": "lightgrey"},
                        "x0": 0 if not self._use_true_base else self._reference_average,
                        "x1": 0 if not self._use_true_base else self._reference_average,
                        "y0": 0,
                        "y1": 1,
                        "xref": "x",
                        "yref": "y domain",
                    }
                ],
            }
        )
        return _layout

    @property
    def figure(self) -> Dict:
        data = self.data

        fig = go.Figure({"data": data, "layout": self.layout})
        if self._show_scatter:
            fig.update_traces(marker_opacity=0.4, text=None)
            for trace in self.scatter_data:
                fig.add_trace(trace)
        return fig
