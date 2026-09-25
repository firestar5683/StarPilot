package cli

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"pfeifer.dev/mapd/cereal/custom"
)

type downloadProgressModel struct {
	output custom.MapdExtendedOut
	valid  bool
}

func (m downloadProgressModel) Update(msg tea.Msg, mm *uiModel) (downloadProgressModel, tea.Cmd) {
	m.valid = mm.extendedDataValid
	m.output = mm.extendedData

	return m, nil
}

func (m downloadProgressModel) View() string {
	if !m.valid {
		return ""
	}
	progress, err := m.output.DownloadProgress()
	if err != nil {
		return ""
	}
	locations := ""
	l, err := progress.Locations()
	if err == nil {
		for i := range l.Len() {
			str, err := l.At(i)
			if err == nil {
				locations += str
				if i < l.Len()-1 {
					locations += ","
				}
			}
		}
	}
	return docStyle.Render(fmt.Sprintf(
		"locations: %s\nactive %t\ncancelled %t\ntotal files: %d\ndownloaded files: %d",
		locations,
		progress.Active(),
		progress.Cancelled(),
		progress.TotalFiles(),
		progress.DownloadedFiles(),
	) + "\n")
}
