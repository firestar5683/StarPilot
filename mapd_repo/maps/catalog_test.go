package maps

import "testing"

func TestBundledManagedRegionCoverage(t *testing.T) {
	regions, err := BundledManagedRegions()
	if err != nil {
		t.Fatal(err)
	}
	if len(regions) != 229 {
		t.Fatalf("bundled catalog changed: %d", len(regions))
	}
	available := 0
	for _, region := range regions {
		if region.Available {
			available++
			if region.Groups < 1 || region.Groups > MaxManagedGroups || region.Unavailable != "" {
				t.Fatalf("invalid available region: %+v", region)
			}
		}
	}
	if available != 199 {
		t.Fatalf("review supported-region count changed: %d", available)
	}
	for token, groups := range map[string]int{"us_state.CA": 36, "us_state.TX": 56, "us_state.IL": 12} {
		region, err := ResolveManagedRegion(token)
		if err != nil || region.Groups != groups {
			t.Fatalf("%s: %+v %v", token, region, err)
		}
	}
	for _, token := range []string{"us_state.AK", "nation.FJ", "nation.RU", "nation.AQ", "nation.US", "nation.CA", "us_state.CA.extra", "nation."} {
		if _, err := ResolveManagedRegion(token); err == nil {
			t.Fatalf("unsupported region %s accepted", token)
		}
	}
}
