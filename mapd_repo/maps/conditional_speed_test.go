package maps

import (
	"testing"
	"time"
)

// 2026-07-13 is a Monday
func mondayAt(hour, minute int) time.Time {
	return time.Date(2026, 7, 13, hour, minute, 0, 0, time.UTC)
}

func saturdayAt(hour, minute int) time.Time {
	return time.Date(2026, 7, 18, hour, minute, 0, 0, time.UTC)
}

func TestParseConditionalSpeeds(t *testing.T) {
	cases := []struct {
		raw   string
		rules int
	}{
		{"30 @ (Mo-Fr 07:00-19:00)", 1},
		{"25 mph @ (Mo-Fr 07:00-17:00)", 1},
		{"100 @ (22:00-06:00)", 1},
		{"30 @ (Sa,Su)", 1},
		{"40 @ (Mo-Fr 07:00-09:00,15:30-17:30); 50 @ (Sa,Su)", 2},
		{"30 @ (Mo-We,Fr 10:00-18:00)", 1},
		// unsupported conditions are dropped, not misapplied
		{"60 @ wet", 0},
		{"30 @ (Mo-Fr 07:00-17:00; PH off)", 0},
		{"90 @ (Nov-Mar)", 0},
		{"30 @ (Mo-Fr 07:00-19:00); 60 @ wet", 1},
		{"none @ (22:00-06:00)", 0},
		{"30", 0},
		{"", 0},
		{"30 @", 0},
	}
	for _, c := range cases {
		if got := len(ParseConditionalSpeeds(c.raw)); got != c.rules {
			t.Errorf("ParseConditionalSpeeds(%q): got %d rules, expected %d", c.raw, got, c.rules)
		}
	}
}

func TestConditionalSpeedAt(t *testing.T) {
	kph := func(v float64) float64 { return v * 0.277778 }
	cases := []struct {
		name     string
		raw      string
		at       time.Time
		expected float64 // 0 = no rule applies
	}{
		{"school zone active", "30 @ (Mo-Fr 07:00-19:00)", mondayAt(8, 30), kph(30)},
		{"school zone evening", "30 @ (Mo-Fr 07:00-19:00)", mondayAt(20, 0), 0},
		{"school zone weekend", "30 @ (Mo-Fr 07:00-19:00)", saturdayAt(8, 30), 0},
		{"mph value", "25 mph @ (Mo-Fr 07:00-17:00)", mondayAt(12, 0), 25 * 0.44704},
		{"night limit before midnight", "100 @ (22:00-06:00)", mondayAt(23, 0), kph(100)},
		{"night limit after midnight", "100 @ (22:00-06:00)", mondayAt(3, 0), kph(100)},
		{"night limit daytime", "100 @ (22:00-06:00)", mondayAt(12, 0), 0},
		{"day only", "30 @ (Sa,Su)", saturdayAt(12, 0), kph(30)},
		{"day only weekday", "30 @ (Sa,Su)", mondayAt(12, 0), 0},
		{"two time ranges gap", "40 @ (Mo-Fr 07:00-09:00,15:30-17:30)", mondayAt(12, 0), 0},
		{"two time ranges second", "40 @ (Mo-Fr 07:00-09:00,15:30-17:30)", mondayAt(16, 0), kph(40)},
		{"later rule wins", "50 @ (Mo-Fr); 30 @ (Mo-Fr 07:00-17:00)", mondayAt(8, 0), kph(30)},
		{"later rule not applying", "50 @ (Mo-Fr); 30 @ (Mo-Fr 07:00-17:00)", mondayAt(20, 0), kph(50)},
		{"boundary start inclusive", "30 @ (Mo-Fr 07:00-19:00)", mondayAt(7, 0), kph(30)},
		{"boundary end exclusive", "30 @ (Mo-Fr 07:00-19:00)", mondayAt(19, 0), 0},
		// Fr 22:00-06:00 extends into Saturday morning, but Saturday evening
		// is not included
		{"overnight day carry", "100 @ (Fr 22:00-06:00)", saturdayAt(3, 0), kph(100)},
		{"overnight day carry end", "100 @ (Fr 22:00-06:00)", saturdayAt(23, 0), 0},
	}
	for _, c := range cases {
		rules := ParseConditionalSpeeds(c.raw)
		got := ConditionalSpeedAt(rules, c.at)
		if diff := got - c.expected; diff > 0.001 || diff < -0.001 {
			t.Errorf("%s: ConditionalSpeedAt(%q, %v) = %v, expected %v", c.name, c.raw, c.at, got, c.expected)
		}
	}
}

func TestParseDaysWrap(t *testing.T) {
	days, ok := parseDays("Sa-Mo")
	if !ok {
		t.Fatalf("Sa-Mo did not parse")
	}
	for day, expected := range map[int]bool{0: true, 1: false, 4: false, 5: true, 6: true} {
		if (days&(1<<day) != 0) != expected {
			t.Errorf("Sa-Mo: day bit %d = %v, expected %v", day, !expected, expected)
		}
	}
}
