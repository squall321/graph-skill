"""Recipe registry. New artifact types register here (one recipe per type)."""

from __future__ import annotations

from .base import Recipe
from .base_xy import BaseXYRecipe
from .cad3d import Cad3dDeformRecipe, Cad3dModeRecipe, Cad3dViewerRecipe, MeshResult3dRecipe
from .cad3d_xtra import Isosurface3dRecipe, PointCloud3dRecipe, Surface3dRecipe
from .batch_h import (
    CampbellRecipe,
    KaplanMeierRecipe,
    MACMatrixRecipe,
    ParisCrackRecipe,
    ProcessCapabilityRecipe,
    WeibullRecipe,
)
from .bode import BodeRecipe, DualAxisRecipe
from .controls import NyquistRecipe, RootLocusRecipe
from .correlation_scatter import CorrelationScatterRecipe
from .diagnostics import ResidualPanelRecipe
from .engineering2d import (
    CFDLineCompareRecipe,
    ConvergenceRecipe,
    InteractionRecipe,
    MainEffectsRecipe,
    NonlinearLoadDispRecipe,
    SNCurveRecipe,
    TransientRecipe,
)
from .fft_spectrum import FFTSpectrumRecipe
from .field2d import FieldRecipe, RainflowRecipe, VectorQuiverRecipe
from .filter_tuner import FilterTunerRecipe
from .flowchart import FlowchartRecipe
from .gauges import BulletChartRecipe, GaugeRecipe, RadialProgressRecipe, StatCardRecipe
from .leftovers import OverviewDetailRecipe, StreamGraphRecipe, SunburstRecipe, TreemapDrilldownRecipe
from .playback import AnimatedTrajectoryRecipe, BarChartRaceRecipe, BubbleTimelineRecipe
from .force_displacement import ForceDisplacementRecipe
from .matrix_compare import MatrixRecipe
from .polar import PolarRecipe, RadarRecipe, RadiationPatternRecipe
from .schedule import (
    CalendarHeatmapRecipe,
    GanttRecipe,
    MilestoneTimelineRecipe,
    TaskTableRecipe,
    WorkPlanRecipe,
)
from .relations import ChordRecipe, NetworkRecipe, SankeyRecipe
from .statistical import BarPlotRecipe, BoxPlotRecipe, ErrorBarRecipe, HistogramRecipe
from .statistical2 import ECDFRecipe, ParetoRecipe, QQRecipe, SPCRecipe
from .stress_strain import StressStrainRecipe
from .wave1 import PdfKdeRecipe, RidgelineRecipe, ScatterMatrixRecipe, SpectrogramRecipe
from .wave2 import AreaPlotRecipe, StackedAreaRecipe, ViolinRecipe, WaterfallRecipe
from .wave3 import NicholsRecipe, ParallelCoordinatesRecipe, SmithChartRecipe, WindRoseRecipe
from .wave4 import CusumRecipe, GoodmanRecipe, PoleZeroRecipe, PsdWelchRecipe
from .wave5 import MultitrackRecipe, ResponseSurfaceRecipe, TreemapRecipe
from .wave6 import EyeDiagramRecipe, GaugeRRRecipe
from .wave7 import (
    ConfusionMatrixRecipe,
    CorrelationMatrixRecipe,
    DecisionMatrixRecipe,
    KpiScorecardRecipe,
)

_matrix = MatrixRecipe()
_field = FieldRecipe()

REGISTRY: dict[str, Recipe] = {
    "base-xy": BaseXYRecipe(),
    "stress-strain": StressStrainRecipe(),
    "force-displacement": ForceDisplacementRecipe(),
    "correlation-scatter": CorrelationScatterRecipe(),
    "histogram": HistogramRecipe(),
    "bar-plot": BarPlotRecipe(),
    "box-plot": BoxPlotRecipe(),
    "error-bar": ErrorBarRecipe(),
    "pareto": ParetoRecipe(),
    "qq-plot": QQRecipe(),
    "ecdf-plot": ECDFRecipe(),
    "spc-control-chart": SPCRecipe(),
    "main-effects-plot": MainEffectsRecipe(),
    "interaction-plot": InteractionRecipe(),
    "transient-time-history": TransientRecipe(),
    "convergence-residual-plot": ConvergenceRecipe(),
    "cfd-line-extract-compare": CFDLineCompareRecipe(),
    "nonlinear-load-displacement": NonlinearLoadDispRecipe(),
    "s-n-fatigue-curve": SNCurveRecipe(),
    "process-capability-hist": ProcessCapabilityRecipe(),
    "paris-crack-growth": ParisCrackRecipe(),
    "campbell-diagram": CampbellRecipe(),
    "kaplan-meier-survival": KaplanMeierRecipe(),
    "mac-matrix-heatmap": MACMatrixRecipe(),
    "nyquist-plot": NyquistRecipe(),
    "root-locus": RootLocusRecipe(),
    "weibull-prob-paper": WeibullRecipe(),
    "dual-axis": DualAxisRecipe(),
    "bode": BodeRecipe(),
    "polar-plot": PolarRecipe(),
    "radar-chart": RadarRecipe(),
    "rf-radiation-pattern": RadiationPatternRecipe(),
    "fft-spectrum": FFTSpectrumRecipe(),
    "filter-tuner": FilterTunerRecipe(),
    "review-matrix": _matrix,
    "design-state-compare": _matrix,
    "single-state-checklist": _matrix,
    "residual-diagnostic-panel": ResidualPanelRecipe(),
    "cad-3d-viewer": Cad3dViewerRecipe(),
    "mesh-result-3d": MeshResult3dRecipe(),
    "mesh-deformed-3d": Cad3dDeformRecipe(),
    "mode-shape-3d": Cad3dModeRecipe(),
    "pdf-kde": PdfKdeRecipe(),
    "ridgeline": RidgelineRecipe(),
    "spectrogram": SpectrogramRecipe(),
    "scatter-matrix": ScatterMatrixRecipe(),
    "area-plot": AreaPlotRecipe(),
    "stacked-area": StackedAreaRecipe(),
    "waterfall-chart": WaterfallRecipe(),
    "violin-plot": ViolinRecipe(),
    "nichols-chart": NicholsRecipe(),
    "parallel-coordinates": ParallelCoordinatesRecipe(),
    "wind-rose": WindRoseRecipe(),
    "smith-chart": SmithChartRecipe(),
    "pole-zero-map": PoleZeroRecipe(),
    "cusum-chart": CusumRecipe(),
    "goodman-haigh": GoodmanRecipe(),
    "psd-welch": PsdWelchRecipe(),
    "multitrack-stack": MultitrackRecipe(),
    "response-surface-2d": ResponseSurfaceRecipe(),
    "treemap": TreemapRecipe(),
    "eye-diagram": EyeDiagramRecipe(),
    "gauge-r-r": GaugeRRRecipe(),
    "correlation-matrix": CorrelationMatrixRecipe(),
    "confusion-matrix": ConfusionMatrixRecipe(),
    "kpi-scorecard": KpiScorecardRecipe(),
    "decision-matrix": DecisionMatrixRecipe(),
    "flowchart": FlowchartRecipe(),
    "bubble-timeline": BubbleTimelineRecipe(),
    "animated-trajectory": AnimatedTrajectoryRecipe(),
    "bar-chart-race": BarChartRaceRecipe(),
    "sankey-diagram": SankeyRecipe(),
    "network-graph": NetworkRecipe(),
    "chord-diagram": ChordRecipe(),
    "gauge": GaugeRecipe(),
    "radial-progress": RadialProgressRecipe(),
    "bullet-chart": BulletChartRecipe(),
    "point-cloud-3d": PointCloud3dRecipe(),
    "surface-3d": Surface3dRecipe(),
    "isosurface-3d": Isosurface3dRecipe(),
    "stat-card": StatCardRecipe(),
    "stream-graph": StreamGraphRecipe(),
    "sunburst": SunburstRecipe(),
    "treemap-drilldown": TreemapDrilldownRecipe(),
    "overview-detail": OverviewDetailRecipe(),
    "gantt-chart": GanttRecipe(),
    "milestone-timeline": MilestoneTimelineRecipe(),
    "calendar-heatmap": CalendarHeatmapRecipe(),
    "task-table": TaskTableRecipe(),
    "work-plan": WorkPlanRecipe(),
    "contour-plot": _field,
    "vector-quiver-2d": VectorQuiverRecipe(),
    "rainflow-cycle-histogram": RainflowRecipe(),
    "heatmap-grid": _field,
    "scalar-field-2d": _field,
    "mcae-stress-contour": _field,
}

__all__ = ["Recipe", "REGISTRY"]
