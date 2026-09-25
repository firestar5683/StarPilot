package maps

import (
	"strconv"
	"strings"
	"time"
)

// Parsed form of one "<speed> @ (<condition>)" rule from an OSM conditional
// restriction like maxspeed:conditional. Only simple day/time conditions are
// supported, rules with anything else (wet, PH, months, ...) are dropped at
// parse time so they can never apply.
type ConditionalSpeedRule struct {
	Speed float64 // m/s
	Days  uint8   // bitmask, bit 0 = Monday .. bit 6 = Sunday
	Times []TimeRange
}

type TimeRange struct {
	Start int // minutes since midnight
	End   int // exclusive; End <= Start means the range wraps past midnight
}

const ALL_DAYS = uint8(0x7F)

var DAY_BITS = map[string]int{
	"Mo": 0,
	"Tu": 1,
	"We": 2,
	"Th": 3,
	"Fr": 4,
	"Sa": 5,
	"Su": 6,
}

// ParseConditionalSpeeds parses an OSM conditional restriction value like
// "40 @ (Mo-Fr 07:00-09:00,15:30-17:30); 100 @ (22:00-06:00)" into the rules
// we can evaluate. Rules whose condition we can't fully evaluate are dropped.
func ParseConditionalSpeeds(raw string) []ConditionalSpeedRule {
	rules := []ConditionalSpeedRule{}
	for _, part := range splitOutsideParens(raw, ';') {
		rule, ok := parseConditionalRule(part)
		if ok {
			rules = append(rules, rule)
		}
	}
	return rules
}

// ConditionalSpeedAt returns the speed of the applying rule at t, or 0 when
// none apply. Later rules take precedence per OSM conditional semantics.
func ConditionalSpeedAt(rules []ConditionalSpeedRule, t time.Time) float64 {
	for i := len(rules) - 1; i >= 0; i-- {
		if rules[i].appliesAt(t) {
			return rules[i].Speed
		}
	}
	return 0
}

// rule separators are ";" outside parentheses, ";" inside parentheses
// separates sub-conditions of one rule
func splitOutsideParens(s string, sep byte) []string {
	parts := []string{}
	depth := 0
	start := 0
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '(':
			depth++
		case ')':
			if depth > 0 {
				depth--
			}
		case sep:
			if depth == 0 {
				parts = append(parts, s[start:i])
				start = i + 1
			}
		}
	}
	return append(parts, s[start:])
}

func parseConditionalRule(part string) (ConditionalSpeedRule, bool) {
	rule := ConditionalSpeedRule{Days: ALL_DAYS}
	valueCondition := strings.SplitN(part, "@", 2)
	if len(valueCondition) != 2 {
		return rule, false
	}
	rule.Speed = ParseMaxSpeed(strings.TrimSpace(valueCondition[0]))
	if rule.Speed <= 0 {
		return rule, false
	}
	condition := strings.TrimSpace(valueCondition[1])
	condition = strings.TrimPrefix(condition, "(")
	condition = strings.TrimSuffix(condition, ")")
	// a ";" inside the parentheses adds a sub-condition like "PH off" that we
	// can't evaluate, so the whole rule is dropped
	if condition == "" || strings.ContainsAny(condition, ";()") {
		return rule, false
	}
	haveDays := false
	for _, token := range strings.Fields(condition) {
		if days, ok := parseDays(token); ok && !haveDays {
			rule.Days = days
			haveDays = true
			continue
		}
		times, ok := parseTimes(token)
		if !ok || len(rule.Times) > 0 {
			return rule, false
		}
		rule.Times = times
	}
	return rule, true
}

func parseDays(token string) (uint8, bool) {
	days := uint8(0)
	for _, group := range strings.Split(token, ",") {
		bounds := strings.Split(group, "-")
		if len(bounds) == 1 {
			bit, ok := DAY_BITS[bounds[0]]
			if !ok {
				return 0, false
			}
			days |= 1 << bit
		} else if len(bounds) == 2 {
			start, okStart := DAY_BITS[bounds[0]]
			end, okEnd := DAY_BITS[bounds[1]]
			if !okStart || !okEnd {
				return 0, false
			}
			for d := start; ; d = (d + 1) % 7 {
				days |= 1 << d
				if d == end {
					break
				}
			}
		} else {
			return 0, false
		}
	}
	return days, days != 0
}

func parseTimes(token string) ([]TimeRange, bool) {
	times := []TimeRange{}
	for _, rangeStr := range strings.Split(token, ",") {
		bounds := strings.Split(rangeStr, "-")
		if len(bounds) != 2 {
			return nil, false
		}
		start, okStart := parseMinutes(bounds[0])
		end, okEnd := parseMinutes(bounds[1])
		if !okStart || !okEnd {
			return nil, false
		}
		times = append(times, TimeRange{Start: start, End: end})
	}
	return times, true
}

func parseMinutes(s string) (int, bool) {
	parts := strings.Split(s, ":")
	if len(parts) != 2 {
		return 0, false
	}
	hours, errHours := strconv.Atoi(parts[0])
	minutes, errMinutes := strconv.Atoi(parts[1])
	if errHours != nil || errMinutes != nil || hours < 0 || hours > 24 || minutes < 0 || minutes > 59 {
		return 0, false
	}
	return hours*60 + minutes, true
}

func (r ConditionalSpeedRule) appliesAt(t time.Time) bool {
	day := (int(t.Weekday()) + 6) % 7 // time.Weekday has Sunday=0, our bit 0 is Monday
	minutes := t.Hour()*60 + t.Minute()
	if len(r.Times) == 0 {
		return r.Days&(1<<day) != 0
	}
	yesterday := (day + 6) % 7
	for _, tr := range r.Times {
		if tr.End > tr.Start {
			if r.Days&(1<<day) != 0 && minutes >= tr.Start && minutes < tr.End {
				return true
			}
		} else {
			// wraps past midnight: the range belongs to the day it starts on
			if r.Days&(1<<day) != 0 && minutes >= tr.Start {
				return true
			}
			if r.Days&(1<<yesterday) != 0 && minutes < tr.End {
				return true
			}
		}
	}
	return false
}
