package maps

import (
	"testing"

	"pfeifer.dev/mapd/cereal/custom"
	"pfeifer.dev/mapd/cereal/offline"
)

func TestHighwayClassFromTag(t *testing.T) {
	cases := map[string]offline.HighwayClass{
		"motorway":       offline.HighwayClass_motorway,
		"motorway_link":  offline.HighwayClass_motorwayLink,
		"trunk":          offline.HighwayClass_trunk,
		"trunk_link":     offline.HighwayClass_trunkLink,
		"primary":        offline.HighwayClass_primary,
		"primary_link":   offline.HighwayClass_primaryLink,
		"secondary":      offline.HighwayClass_secondary,
		"secondary_link": offline.HighwayClass_secondaryLink,
		"tertiary":       offline.HighwayClass_tertiary,
		"tertiary_link":  offline.HighwayClass_tertiaryLink,
		"unclassified":   offline.HighwayClass_unclassified,
		"residential":    offline.HighwayClass_residential,
		"living_street":  offline.HighwayClass_livingStreet,
		// tags without a class of their own fall back to unknown
		"":         offline.HighwayClass_unknown,
		"service":  offline.HighwayClass_unknown,
		"footway":  offline.HighwayClass_unknown,
		"Motorway": offline.HighwayClass_unknown,
	}
	for tag, expected := range cases {
		if class := HighwayClassFromTag(tag); class != expected {
			t.Errorf("HighwayClassFromTag(%q) = %v, expected %v", tag, class, expected)
		}
	}
}

// state.go converts the offline enum to the custom (mapdOut) enum with a
// direct cast, so the two generated enums must agree name-for-name and
// value-for-value. Iterating until both String() results are empty (the
// generated default for out-of-range values) also catches a value appended to
// only one of the two schemas.
func TestHighwayClassEnumsInSync(t *testing.T) {
	for value := offline.HighwayClass(0); value < 1000; value++ {
		offlineName := value.String()
		customName := custom.HighwayClass(value).String()
		if offlineName == "" && customName == "" {
			return
		}
		if offlineName != customName {
			t.Errorf("enum mismatch at value %d: offline=%q custom=%q", value, offlineName, customName)
		}
	}
}

// Every tag that maps to a stored class should also have a rank in the
// highway hierarchy table.
func TestHighwayClassTagsHaveRank(t *testing.T) {
	for tag := range HIGHWAY_TAG_TO_CLASS {
		if _, ok := HIGHWAY_RANK[tag]; !ok {
			t.Errorf("tag %q has a highway class but no HIGHWAY_RANK entry", tag)
		}
	}
}
