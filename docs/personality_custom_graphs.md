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
braking authority or change acceleration/braking preset definitions.

## Following presets

Named following presets now match Dom's factory following settings with custom
personalities enabled. Close follows Aggressive, Medium follows Standard and
Far follows Relaxed. The presets are available in every personality.

| Preset | Previous curve | Revised curve |
| --- | --- | --- |
| Close | 1.25 s at every speed | 1.25 s through 45 mph, falling to 1.0 s at 70 mph |
| Medium | 1.45 s at every speed | 1.45 s through 45 mph, falling to 1.2 s at 70 mph |
| Far | 1.75 s at every speed | 1.6 s through 45 mph, falling to 1.4 s at 70 mph |
| Traffic | No named preset | 0.75 s at rest, rising to 1.6 s at 25 m/s (55.92 mph) |

Interpolation is linear between the stated breakpoints and constant outside
them. Named presets use the exact native speed axes at runtime. First-use
Custom conversion samples them onto the existing 10 mph editor grid.

Existing v1/v2 Close, Medium and Far selections keep their old fixed headways
as `legacy_close`, `legacy_medium` and `legacy_far`. Both Galaxy pickers show
the selected compatibility entry as **Previous Close**, **Previous Medium**
or **Previous Far**. Explicitly selecting a current preset adopts its new curve.
The previous entry disappears when it is no longer selected.

Existing `dom_default` selections continue to inherit configured settings;
they are not silently converted to fixed named presets. Fresh profiles also
retain this inheritance. The named curves match untouched factory settings;
users' changed global following values can still differ from them.

Acceleration and braking presets are unchanged. Standard acceleration and Eco
braking match the normal factory defaults for Aggressive, Standard and Relaxed
when named-preset and global powertrain tuning agree. Named presets use detected
EV/truck tuning; the Dom-default resolver respects the global tuning switches,
so these can differ. Traffic retains its dedicated acceleration/braking defaults;
this change adds only its named following preset.

## Storage compatibility

Profile document version 3 retains `curve` and optional `legacyCurve` while
`preset` is a named preset or `dom_default`. These retained values are dormant;
only Custom uses them. An actual graph edit or reset retires preserved v1
interpolation for that category; a preset switch or unchanged submission does
not.

Valid v2 documents retain their runtime meaning and are upgraded on the next
normal write, including the fixed following compatibility names above.
Version 1 keeps its existing explicit, verified migration flow. Reads never
rewrite Params. Category conflict detection, off-road checks and atomic profile
document writes still apply to edits and resets.

Older builds do not understand v3 documents. Retain a compatible settings
backup before rolling back to one of those builds. Curves discarded before
this change cannot be recovered automatically.
