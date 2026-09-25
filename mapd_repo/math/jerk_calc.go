package math

import "math"

// JerkProfile represents a complete jerk-limited motion profile
type JerkProfile struct {
	// Phase 1: Jerk from a0 to aMax
	T1 float32 // Duration of first jerk phase
	V1 float32 // Velocity at end of phase 1
	D1 float32 // Distance traveled in phase 1
	A1 float32 // Acceleration at end of phase 1 (should equal aMax or final accel if target reached early)

	// Phase 2: Constant acceleration
	T2 float32 // Duration of constant acceleration phase
	V2 float32 // Velocity at end of phase 2
	D2 float32 // Distance traveled in phase 2

	// Phase 3: Jerk from aMax to 0
	T3 float32 // Duration of final jerk phase
	V3 float32 // Velocity at end of phase 3 (should equal target velocity)
	D3 float32 // Distance traveled in phase 3

	// Total
	TotalTime     float32 // Total time for profile
	TotalDistance float32 // Total distance for profile
}

// CalculateJerkLimitedDistance calculates the distance required to reach a target velocity
// with jerk-limited acceleration profile.
//
// Parameters:
//
//	v0: Current velocity (m/s)
//	a0: Current acceleration (m/s²)
//	vTarget: Target velocity (m/s)
//	aMax: Maximum acceleration magnitude (m/s²) - always positive
//	jMax: Maximum jerk magnitude (m/s³) - always positive
//
// Returns the total distance required and complete motion profile
func CalculateJerkLimitedDistance(v0, a0, vTarget, aMax, jMax float32) (float32, JerkProfile) {
	profile := JerkProfile{}

	// Determine direction (accelerating or decelerating)
	accelerating := vTarget > v0

	// Set signs for acceleration and jerk based on direction
	var aTarget, jTarget float32
	if accelerating {
		aTarget = aMax
		// If current acceleration is already above target, start decelerating the acceleration
		if a0 > aTarget {
			jTarget = -jMax
		} else {
			jTarget = jMax
		}
	} else {
		// Decelerating toward lower velocity
		aTarget = -aMax
		// If current acceleration is already below target (more negative), increase it
		if a0 < aTarget {
			jTarget = jMax
		} else {
			jTarget = -jMax
		}
	}

	// Phase 1: Change acceleration from a0 toward aTarget using jerk
	aDiff := aTarget - a0

	// Check if we need to change acceleration at all
	if Abs(aDiff) < 0.001 {
		// Already at target acceleration, skip to constant acceleration phase
		profile.T1 = 0
		profile.V1 = v0
		profile.D1 = 0
		profile.A1 = a0
		jTarget = 0 // No jerk needed
	} else {
		// Time to reach target acceleration
		profile.T1 = float32(Abs(aDiff / jTarget))

		// Check if we reach target velocity before reaching target acceleration
		// Velocity after jerk phase: v = v0 + a0*t + 0.5*j*t²
		vAfterJerk := v0 + a0*profile.T1 + 0.5*jTarget*profile.T1*profile.T1

		velocityReached := (accelerating && vAfterJerk >= vTarget) || (!accelerating && vAfterJerk <= vTarget)

		if velocityReached {
			// We reach target velocity during jerk phase
			// Solve: vTarget = v0 + a0*t + 0.5*j*t²
			// Rearrange: 0.5*j*t² + a0*t + (v0 - vTarget) = 0
			a := 0.5 * jTarget
			b := a0
			c := v0 - vTarget

			discriminant := b*b - 4*a*c
			if discriminant < 0 {
				// No solution, use full jerk phase
				profile.V1 = vAfterJerk
				profile.A1 = aTarget
			} else {
				// Select positive root
				sqrtDisc := float32(math.Sqrt(float64(discriminant)))
				t1 := (-b + sqrtDisc) / (2 * a)
				t2 := (-b - sqrtDisc) / (2 * a)

				if t1 > 0 && (t2 <= 0 || t1 < t2) {
					profile.T1 = t1
				} else if t2 > 0 {
					profile.T1 = t2
				}

				profile.V1 = vTarget
				profile.A1 = a0 + jTarget*profile.T1
			}
		} else {
			// Normal case: complete the jerk phase
			profile.V1 = vAfterJerk
			profile.A1 = aTarget
		}

		// Distance during jerk phase: d = v0*t + 0.5*a0*t² + (1/6)*j*t³
		profile.D1 = v0*profile.T1 + 0.5*a0*profile.T1*profile.T1 + (1.0/6.0)*jTarget*profile.T1*profile.T1*profile.T1
	}

	// Phase 2: Constant acceleration (if target not yet reached)
	vRemaining := vTarget - profile.V1
	needsPhase2 := (accelerating && vRemaining > 0.001) || (!accelerating && vRemaining < -0.001)

	if needsPhase2 && Abs(profile.A1) > 0.001 {
		// Time for constant acceleration: t = Δv / a
		profile.T2 = vRemaining / profile.A1
		profile.V2 = vTarget

		// Distance during constant acceleration: d = v*t + 0.5*a*t²
		profile.D2 = profile.V1*profile.T2 + 0.5*profile.A1*profile.T2*profile.T2
	} else {
		profile.T2 = 0
		profile.V2 = profile.V1
		profile.D2 = 0
	}

	// Phase 3: Decelerate acceleration back to 0 (for smooth arrival)
	// This phase is often included for comfort, but may be optional depending on requirements
	// For now, we'll skip it as the question focuses on reaching the target velocity
	profile.T3 = 0
	profile.V3 = profile.V2
	profile.D3 = 0

	// Calculate totals
	profile.TotalTime = profile.T1 + profile.T2 + profile.T3
	profile.TotalDistance = profile.D1 + profile.D2 + profile.D3

	return profile.TotalDistance, profile
}

// CalculateJerkLimitedDistanceSimple is a simplified version that just returns the distance
func CalculateJerkLimitedDistanceSimple(v0, a0, vTarget, aMax, jMax float32) float32 {
	distance, _ := CalculateJerkLimitedDistance(v0, a0, vTarget, aMax, jMax)
	return distance
}
