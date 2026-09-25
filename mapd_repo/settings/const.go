package settings

import (
	_ "embed"
	"math"
	"time"

	"github.com/pfeiferj/gomsgq"
)

const (
	// Queue sizes matching openpilot's services.py
	QUEUE_SIZE_LEGACY    = 10 * 1024 * 1024 // 10MB - Used by all services in previous versions of msgq/openpilot
	QUEUE_SIZE_BIG       = 10 * 1024 * 1024 // 10MB - modelV2, video encoders
	QUEUE_SIZE_MEDIUM    = 2 * 1024 * 1024  // 2MB - CAN, controlsState
	QUEUE_SIZE_SMALL     = 250 * 1024       // 250KB - most services
	DEFAULT_SEGMENT_SIZE = 1 * 1024 * 1024  // 1MB - services not in openpilot list

	LOOP_DELAY                   = 50 * time.Millisecond
	MS_TO_KPH                    = 3.6
	MS_TO_MPH                    = 2.237
	MS_TO_KNOTS                  = 1.944
	KPH_TO_MS                    = 1 / MS_TO_KPH
	MPH_TO_MS                    = 1 / MS_TO_MPH
	KNOTS_TO_MS                  = 1 / MS_TO_KNOTS
	ENABLE_SPEED_RANGE           = 0.2       // m/s
	R                            = 6373000.0 // approximate radius of earth in meters
	TO_RADIANS                   = math.Pi / 180
	TO_DEGREES                   = 180 / math.Pi
	QUERY_RADIUS                 = float64(3000)       // meters
	PADDING                      = 10 / R * TO_DEGREES // 10 meters in degrees
	GROUP_AREA_BOX_DEGREES       = 2
	AREA_BOX_DEGREES             = float64(1.0 / 4) // Must be 1.0 divided by an integer number
	WAYS_PER_FILE                = 2000
	MAX_OP_SPEED                 = 90 * MPH_TO_MS
	ACCEPTABLE_BEARING_DELTA_SIN = 0.7071067811865475 // sin(45°) - max acceptable bearing mismatch
	MIN_WAY_DIST                 = 500                // meters. how many meters to look ahead before stopping gathering next ways.
	CURVE_CALC_OFFSET            = 10 * MPH_TO_MS
)

// ServiceQueueSize maps service names to their queue sizes from openpilot's services.py
var ServiceQueueSize = map[string]int64{
	// BIG (10MB)
	"modelV2":            QUEUE_SIZE_BIG,
	"modelDataV2SP":      QUEUE_SIZE_BIG,
	"can":                QUEUE_SIZE_BIG,
	"procLog":            QUEUE_SIZE_BIG,
	"roadEncodeData":     QUEUE_SIZE_BIG,
	"driverEncodeData":   QUEUE_SIZE_BIG,
	"wideRoadEncodeData": QUEUE_SIZE_BIG,
	"qRoadEncodeData":    QUEUE_SIZE_BIG,

	// MEDIUM (2MB)
	"controlsState": QUEUE_SIZE_MEDIUM,
	"sendcan":       QUEUE_SIZE_MEDIUM,

	// SMALL (250KB) - most services
	"carState":            QUEUE_SIZE_SMALL,
	"carControl":          QUEUE_SIZE_SMALL,
	"carOutput":           QUEUE_SIZE_SMALL,
	"selfdriveState":      QUEUE_SIZE_SMALL,
	"gpsLocation":         QUEUE_SIZE_SMALL,
	"gpsLocationExternal": QUEUE_SIZE_SMALL,
	"liveLocationKalman":  QUEUE_SIZE_SMALL,
	"gpsNMEA":             QUEUE_SIZE_SMALL,
	"ubloxGnss":           QUEUE_SIZE_SMALL,
	"qcomGnss":            QUEUE_SIZE_SMALL,
	"gnssMeasurements":    QUEUE_SIZE_SMALL,

	// mapd
	"mapdOut":         QUEUE_SIZE_MEDIUM,
	"mapdExtendedOut": QUEUE_SIZE_MEDIUM,
	"mapdIn":          QUEUE_SIZE_MEDIUM,
	"mapdCli":         QUEUE_SIZE_MEDIUM,
}

// GetSegmentSize returns the appropriate segment size for a service
func GetSegmentSize(service string) int64 {
	isPrefixed := gomsgq.IsPrefixedMsgq()
	if !isPrefixed {
		return QUEUE_SIZE_LEGACY
	}
	if size, ok := ServiceQueueSize[service]; ok {
		return size
	}
	// Default to SMALL (250KB) to matches op default queue size
	return QUEUE_SIZE_SMALL
}

//go:embed download_menu.json
var boundingBoxesJson []byte

//go:embed defaults.json
var defaultsJson []byte

//go:embed recommended.json
var recommendedJson []byte
