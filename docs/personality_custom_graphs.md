# Custom personality graphs

Each personality keeps its own Custom acceleration, braking and following curve.
Selecting a named preset changes the active selection without deleting Custom
points. Selecting Custom again restores those points, including after a reload
or restart. If a category has never had Custom points, it is initialized from
the current selection, as before.

The existing **Reset to default** button, below each Custom graph's numeric
points in New Galaxy's Advanced section, replaces only that category's Custom
curve. It leaves the category set to Custom. The server resolves the reset
values; the dashed **Dom default** line uses the same resolver.

Defaults are Dom's configured base curves sampled at the editor's 10 mph
points. They include Traffic's dedicated acceleration and braking, following
settings, global tuning switches and powertrain overrides. Where gear mapping
is enabled, the reference uses normal gear. Live Eco/Sport gear, weather,
lead/stop and overspeed adjustments remain on the existing controller paths.
Sampling cannot reproduce every native breakpoint or between-point value;
resetting a Custom graph is not the same as delegating to the Dom-default
runtime path.

Dom-default points outside the ordinary editor range (such as Traffic braking
at 0.35 m/s², configured Traffic following at 0.5 seconds or truck acceleration
at 6 m/s²) remain visible and are preserved when another point is edited.
New point edits still use the existing authoring bounds. This does not expand
braking authority or change named-preset controller behaviour.

## Storage compatibility

Profile document version 3 retains `curve` and optional `legacyCurve` while
`preset` is a named preset or `dom_default`. These retained values are dormant;
only Custom uses them. An actual graph edit or reset retires preserved v1
interpolation for that category; a preset switch or unchanged submission does
not.

Valid v2 documents are read losslessly and upgraded on the next normal write.
Version 1 keeps its existing explicit, verified migration flow. Reads never
rewrite Params. Category conflict detection, off-road checks and atomic profile
document writes still apply to edits and resets.

Older builds do not understand v3 documents. Retain a compatible settings
backup before rolling back to one of those builds. Curves discarded before
this change cannot be recovered automatically.
