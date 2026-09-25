package cli

import (
	"fmt"
	"math"

	tea "github.com/charmbracelet/bubbletea"
	"pfeifer.dev/mapd/cereal/custom"
)

type outputModel struct {
	output         custom.MapdOut
	extendedOutput custom.MapdExtendedOut
	valid          bool
	extendedValid  bool
	height, width  int
}

func (m outputModel) Update(msg tea.Msg, mm *uiModel) (outputModel, tea.Cmd) {
	out, success := mm.sub.Read()
	if success {
		m.valid = true
		m.output = out
	}
	m.extendedValid = mm.extendedDataValid
	m.extendedOutput = mm.extendedData

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		h, v := docStyle.GetFrameSize()
		m.width = msg.Width - h
		m.height = msg.Height - v
	}

	return m, nil
}

func (m outputModel) View() string {
	if !m.valid || !m.extendedValid {
		return ""
	}
	path, _ := m.extendedOutput.Path()
	minLat := 180.0
	minLon := 180.0
	maxLat := -180.0
	maxLon := -180.0
	for i := range path.Len() {
		point := path.At(i)
		if point.Latitude() < minLat {
			minLat = point.Latitude()
		}
		if point.Longitude() < minLon {
			minLon = point.Longitude()
		}
		if point.Latitude() > maxLat {
			maxLat = point.Latitude()
		}
		if point.Longitude() > maxLon {
			maxLon = point.Longitude()
		}
	}
	latRange := maxLat - minLat
	lonRange := maxLon - minLon
	gHeight := m.height - 15
	gWidth := m.width
	if gHeight < gWidth/2 {
		gWidth = gHeight * 2
	} else {
		gHeight = gWidth / 2
	}

	grid := make([]byte, int(gWidth*gHeight+gHeight+1))
	for i := range int(gWidth*gHeight + gHeight + 1) {
		if i%(gWidth+1) == 0 && i != 0 {
			grid[i] = '\n'
		} else {
			grid[i] = ' '
		}
	}
	if latRange != 0 && lonRange != 0 {
		aspect := latRange / lonRange
		if lonRange > latRange {
			aspect = lonRange / latRange
		}
		for i := range path.Len() {
			point := path.At(i)
			y := (point.Latitude() - minLat) / latRange
			x := (lonRange - (point.Longitude() - minLon)) / lonRange
			if latRange > lonRange {
				x /= aspect
			} else {
				y /= aspect
			}
			idx := int(math.Floor(x*float64(gWidth)) + (math.Floor(y*float64(gHeight-1)) * (float64(gWidth) + 1)))
			if idx%(gWidth+1) == 0 {
				idx += 1
			}
			grid[idx] = '#'
		}
		position, err := m.extendedOutput.Position()
		if err == nil {
			y := (position.Latitude() - minLat) / latRange
			x := (lonRange - (position.Longitude() - minLon)) / lonRange
			if latRange > lonRange {
				x /= aspect
			} else {
				y /= aspect
			}
			idx := int(math.Floor(x*float64(gWidth)) + (math.Floor(y*float64(gHeight-1)) * (float64(gWidth) + 1)))
			if idx%(gWidth+1) == 0 {
				idx += 1
			}
			if idx < len(grid) {
				grid[idx] = 'X'
			}
		}
	}

	roadname, _ := m.output.RoadName()
	return docStyle.Render(fmt.Sprintf(
		"name: %s\nsuggested speed: %f\nspeed limit: %f\nspeed limit suggested speed: %f\nnext speed limit: %f\nnext speed limit distance: %f\nvision curve speed: %f\nmap curve speed: %f\ndistance from center: %f\nlanes: %d\nhighway class: %s\nselection type: %s\nloop rate average: %f\nloop rate min: %f\n\n%s",
		roadname,
		m.output.SuggestedSpeed(),
		m.output.SpeedLimit(),
		m.output.SpeedLimitSuggestedSpeed(),
		m.output.NextSpeedLimit(),
		m.output.NextSpeedLimitDistance(),
		m.output.VisionCurveSpeed(),
		m.output.MapCurveSpeed(),
		m.output.DistanceFromWayCenter(),
		m.output.Lanes(),
		m.output.HighwayClass().String(),
		m.output.WaySelectionType().String(),
		m.extendedOutput.LoopRateAverage(),
		m.extendedOutput.LoopRateMin(),
		string(grid),
	) + "\n")
}
