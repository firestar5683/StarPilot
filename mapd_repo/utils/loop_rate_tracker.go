package utils

import "time"

const LoopRateTrackerSize = 20

// LoopRateTracker keeps a ring buffer of the last LoopRateTrackerSize cycle
// durations so callers can report an average and minimum loop update rate.
type LoopRateTracker struct {
	durations [LoopRateTrackerSize]time.Duration
	index     int
	count     int
}

func (t *LoopRateTracker) Add(d time.Duration) {
	t.durations[t.index] = d
	t.index = (t.index + 1) % LoopRateTrackerSize
	if t.count < LoopRateTrackerSize {
		t.count++
	}
}

// AverageRate returns the average update rate, in Hz, over the tracked cycles.
func (t *LoopRateTracker) AverageRate() float64 {
	if t.count == 0 {
		return 0
	}
	var total time.Duration
	for i := 0; i < t.count; i++ {
		total += t.durations[i]
	}
	avg := total / time.Duration(t.count)
	if avg <= 0 {
		return 0
	}
	return float64(time.Second) / float64(avg)
}

// MinRate returns the slowest (minimum) update rate, in Hz, over the tracked
// cycles — i.e. the rate implied by the longest single cycle duration.
func (t *LoopRateTracker) MinRate() float64 {
	if t.count == 0 {
		return 0
	}
	longest := t.durations[0]
	for i := 1; i < t.count; i++ {
		if t.durations[i] > longest {
			longest = t.durations[i]
		}
	}
	if longest <= 0 {
		return 0
	}
	return float64(time.Second) / float64(longest)
}
