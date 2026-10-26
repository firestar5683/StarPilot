"""SP-016 v4 scalar preferences shared by runtime and settings presentation."""
import math
from numbers import Real

PREFIX = "LaneCenteringV4"
STOCK_CORRECTION = 0.004 * 0.30
MAX_CORRECTION = 2 * STOCK_CORRECTION
# field: suffix, default, minimum, maximum, step, display unit, label, description, page
NUMBERS = {
  "min_speed_mps": ("MinSpeed", 0.0, 0., 45 * .44704, .44704, "speed", "Minimum speed", "Set the lowest speed at which lane centering can activate. Below this speed, no lane-centering correction is added to the driving model.", "activation"),
  "max_correction": ("MaxCorrection", 0.0018, STOCK_CORRECTION, MAX_CORRECTION, STOCK_CORRECTION / 100, "% of stock", "Maximum correction", "Limit how much correction lane centering can request. Higher values allow more correction.", "preferences"),
  "max_width": ("MaxWidth", 4.8, 2., 10., .01, "m", "Maximum lane width", "Set the maximum lane width for centring between two boundaries. If the detected lane is wider than this, centring pauses, but correction away from a nearby single boundary can still operate.", "geometry"),
  "confidence_split": ("ConfidenceSplit", 0.2, 0., 1., .01, "%", "Minimum confidence", "Lane lines with confidence at or above this value use the higher-confidence uncertainty limit. Higher values require more confidence. Lines below this value may still be accepted using the lower-confidence settings.", "higher_confidence"),
  "min_confidence": ("MinConfidence", 0.1, 0., 1., .01, "%", "Minimum confidence", "Lane lines must have confidence at or above this value to be accepted. Higher values accept fewer lines. Lines must also pass the applicable position-uncertainty limit.", "lower_confidence"),
  "high_std": ("HighStd", 1.0, 0., 3., .05, "m", "Maximum position uncertainty", "Higher-confidence lane lines are only accepted if their position uncertainty is below this value. Higher values accept more lines; lower values require more precise positions.", "higher_confidence"),
  "low_std": ("LowStd", 0.6, 0., 3., .05, "m", "Maximum position uncertainty", "Lower-confidence lane lines are only accepted if their position uncertainty is below this value. Higher values accept more lines; lower values require more precise positions.", "lower_confidence"),
  "edge_std": ("EdgeStd", 1.0, 0., 3., .05, "m", "Road edge maximum position uncertainty", "Road edges are only accepted if their position uncertainty is below this value. Higher values accept more edges; lower values require more precise positions. Road edges do not have a separate confidence threshold.", "acceptance"),
  "car_width": ("CarWidth", 1.85, 1., 3., .01, "m", "Car body width", "Enter the width of your car in metres, excluding mirrors. This is combined with your clearance settings to calculate the minimum gap for centring between two boundaries and the target distance from a single boundary.", "geometry"),
  "clearance": ("Clearance", 0.0, 0., 1., .01, "cm", "Two-boundary minimum clearance", "Sets the minimum lane width that lane centering can use. This is calculated as your car body width plus twice this clearance, allowing that much extra space on each side. Centring between two boundaries only activates when their gap meets this minimum.", "geometry"),
  "smoothing_tau": ("SmoothingTime", 0.2, 0., 1., .01, "s", "Boundary smoothing time", "Smooth changes in detected lane-line and road-edge positions before calculating correction. Higher values reduce small movements but respond more slowly to position changes; lower values follow detections faster. Zero disables boundary smoothing. Measured in seconds.", "smoothing"),
  "smoothing_distance": ("SmoothingDistance", 0.25, 0., .5, .01, "cm", "Maximum boundary smoothing distance", "Limit how far a smoothed lane line or road edge can lag behind its latest detected position. Higher values allow more smoothing; lower values keep it closer to the detection. This limits lag, not movement per update. Zero disables boundary smoothing. Measured in centimetres.", "smoothing"),
  "response_tau": ("ResponseTime", 0.35, 0., 1., .01, "s", "Maximum correction response time", "Normal response time in seconds, also used with Curve adaptation off. With adaptation on, tighter bends reduce this toward Minimum correction response time. Smooths changes including reductions and reversals; lower is quicker, not stronger.", "smoothing"),
  "release_tau": ("ReleaseTime", 0.2, 0., 1., .01, "s", "Return-to-model time", "Set how quickly lane-centering correction fades away when centering pauses or suitable boundaries are lost. Lower values return to the model path faster; higher values make the transition more gradual. Zero removes the correction immediately. Measured in seconds.", "smoothing"),
  "single_deadband": ("SingleDeadband", 0.02, 0., .15, .01, "cm", "Deadband", "Ignore this much difference from the lane-centre target, or shortfall from a single-boundary clearance target, before requesting correction. Lower values correct smaller differences but may increase steering activity; higher values allow more variation. Applies to all lane-centering corrections. Measured in centimetres.", "preferences"),
  "lookahead_time": ("LookaheadTime", 1.0, .5, 2., .05, "s", "Lookahead time", "Set how far ahead lane centering samples the model path, boundaries and bend shape. Distance is speed multiplied by this time, limited to 8-35 metres. Higher values look farther ahead. This also changes the correction calculation: for the same path difference, a longer distance requests less correction. Measured in seconds.", "preferences"),
  "override_start": ("OverrideStart", .15, 0., 1., .01, "cm", "Start model override", "Path disagreement where a confident model begins reducing lane correction. Lower values allow reduction sooner. Must be below Full model override. Measured in centimetres.", "preferences"),
  "override_full": ("OverrideFull", .50, 0., 1., .01, "cm", "Full model override", "Path disagreement where the full reduction allowed by the current Model path preference is reached. Lower values reach that reduction sooner. Must exceed Start model override. Measured in centimetres.", "preferences"),
  "single_clearance": ("SingleClearance", 0.45, 0., 1., .01, "cm", "Single-boundary minimum clearance", "Set the extra space to aim for between the side of your car and a single lane line or road edge. If the model path comes too close, lane centering requests correction away from that boundary. It does not request correction towards it. The target distance from the centre of the car is half your car body width plus this clearance.", "geometry"),
  "response_min": ("ResponseMin", 0.1, 0., 1., .01, "s", "Minimum correction response time", "Response time at the tightest bends, in seconds. Lower follows changing correction targets faster but can increase jitter. Must not exceed Maximum correction response time. When road shape is unknown, keep the last effective value. Preference falls quickly for bends and rises about 95% toward a steady target in one second.", "smoothing"),
  "e2e_min": ("E2EMin", 0.0, 0., 1., .05, "%", "Minimum model path preference", "Model preference at the tightest bends. Lower allows less confidence-dependent reduction of lane correction. Must not exceed the normal maximum; 0% at both ends disables that reduction. When road shape is unknown, keep the last effective value. Preference falls quickly for bends and rises about 95% toward a steady target in one second.", "preferences"),
  "curve_start_radius": ("CurveStartRadius", 2000.0, 100., 3000., 25., "m", "Maximum corner radius", "Bend-start radius in metres. Below this radius, adaptation progressively reduces response time and model preference. Larger starts on gentler bends. Must exceed Minimum corner radius.", "curves"),
  "curve_full_radius": ("CurveFullRadius", 250.0, 25., 1000., 25., "m", "Minimum corner radius", "Full-adaptation radius in metres. At this radius or tighter, use minimum response time and model preference. Larger reaches full adaptation on gentler bends. Must be below Maximum corner radius.", "curves"),

}
# SingleDeadband retains its saved key for compatibility; it now applies to every mode.
# Legacy mode preferences are ignored: live selection always considers all boundaries.
BOOLS = {"curve_adaptation": PREFIX + "CurveAdaptation"}
KEYS = frozenset([PREFIX + row[0] for row in NUMBERS.values()] + list(BOOLS.values()))
DEFAULTS = {PREFIX + row[0]: row[1] for row in NUMBERS.values()} | {key: True for key in BOOLS.values()}
BEND_KEYS = frozenset(PREFIX + name for name in ("ResponseMin", "E2EMin", "CurveStartRadius", "CurveFullRadius"))
ADAPTATION = PREFIX + "CurveAdaptation"
GEOMETRY_KEYS = tuple(PREFIX + name for name in ("CarWidth", "Clearance", "MaxWidth"))
PAIRS = {PREFIX + "MinConfidence": PREFIX + "ConfidenceSplit", PREFIX + "ConfidenceSplit": PREFIX + "MinConfidence"}

def valid_tuning(settings):
  try:
    for field, (_, _, low, high, *_) in NUMBERS.items():
      value = getattr(settings, field)
      if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or not low <= value <= high:
        return False
    return (all(type(getattr(settings, name)) is bool for name in BOOLS) and
            settings.min_width < settings.max_width and settings.min_confidence <= settings.confidence_split and
            settings.response_min <= settings.response_tau and settings.e2e_min <= settings.e2e_authority and
            settings.curve_full_radius < settings.curve_start_radius and settings.override_start < settings.override_full)
  except (TypeError, ValueError, OverflowError):
    return False
