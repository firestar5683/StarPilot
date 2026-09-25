package math

type MovingAverage struct {
	values      []float64
	index       int
	size        int
	initialized bool
	Estimate    float64
}

func (a *MovingAverage) Init(size int) {
	a.size = size
	a.values = make([]float64, size)
	a.initialized = false
	a.index = 0
}

func (a *MovingAverage) Reset() {
	a.initialized = false
}

func (a *MovingAverage) Update(val float64) float64 {
	corrected := val
	if corrected == 0 { // prevent divide by zero issues
		corrected = 0.01
	}
	if !a.initialized {
		for i := range a.values {
			a.values[i] = corrected
		}
		a.initialized = true
		a.Estimate = corrected
		return corrected
	}
	a.index += 1
	a.index %= a.size
	a.values[a.index] = corrected
	total := 0.0
	for _, v := range a.values {
		total += v
	}
	a.Estimate = total / float64(a.size)
	return a.Estimate
}

func (a *MovingAverage) Raw() float64 {
	return a.values[a.index]
}
