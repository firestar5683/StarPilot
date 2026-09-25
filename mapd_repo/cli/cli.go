package cli

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/urfave/cli/v3"
	"pfeifer.dev/mapd/maps"
	m "pfeifer.dev/mapd/math"
	"pfeifer.dev/mapd/params"
)

func Handle() {
	shouldExit := true
	cmd := &cli.Command{
		Commands: []*cli.Command{
			{
				Name:    "interactive",
				Aliases: []string{"i"},
				Usage:   "Send commands to an active mapd instance",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					interactive()
					return nil
				},
			},
			{
				Name:    "generate",
				Aliases: []string{"g"},
				Flags: []cli.Flag{
					&cli.Float64Flag{
						Category: "Bounds",
						Name:     "minlat",
						Usage:    "Sets the minimum latitude in degrees used while generating offline maps",
						Value:    -90,
					},
					&cli.Float64Flag{
						Category: "Bounds",
						Name:     "minlon",
						Usage:    "Sets the minimum longitude in degrees used while generating offline maps",
						Value:    -180,
					},
					&cli.Float64Flag{
						Category: "Bounds",
						Name:     "maxlat",
						Usage:    "Sets the maximum latitude in degrees used while generating offline maps",
						Value:    90,
					},
					&cli.Float64Flag{
						Category: "Bounds",
						Name:     "maxlon",
						Usage:    "Sets the maximum longitude in degrees used while generating offline maps",
						Value:    180,
					},
					&cli.Float64Flag{
						Category: "Bounds",
						Name:     "overlap",
						Usage:    "Sets the amount in degrees to overlap each offline tile",
						Value:    0.001,
					},
					&cli.StringFlag{
						Category: "Inputs and Outputs",
						Name:     "input-file",
						Usage:    "The open street maps pbf file to generate offline map files from",
						Aliases: []string{
							"i",
						},
						Value: "./map.osm.pbf",
					},
					&cli.StringFlag{
						Category: "Inputs and Outputs",
						Aliases: []string{
							"o",
						},
						Usage: "The base directory to output the offline map files to",
						Name:  "output-directory",
						Value: fmt.Sprintf("%s/offline", params.GetBaseOpPath()),
					},
					&cli.BoolFlag{
						Category: "Inputs and Outputs",
						Name:     "generate-empty-files",
						Usage:    "Generates map tiles that have no roads",
						Aliases: []string{
							"e",
						},
						Value: false,
					},
				},
				Usage: "Triggers a generation of map data from the pbf given by --input-file",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					offlineSettings := maps.OfflineSettings{
						Box: m.Box{
							MinPos: m.NewPosition(cmd.Float64("minlat"), cmd.Float64("minlon")),
							MaxPos: m.NewPosition(cmd.Float64("maxlat"), cmd.Float64("maxlon")),
						},
						Overlap:            cmd.Float64("overlap"),
						InputFile:          cmd.String("input-file"),
						OutputDirectory:    cmd.String("output-directory"),
						GenerateEmptyFiles: cmd.Bool("generate-empty-files"),
					}
					return maps.GenerateOffline(offlineSettings)
				},
			},
		},
		Name:  "Mapd",
		Usage: "Start an instance of mapd",
		Action: func(ctx context.Context, cmd *cli.Command) error {
			shouldExit = false
			return nil
		},
	}

	if err := cmd.Run(context.Background(), os.Args); err != nil {
		log.Fatal(err)
	}

	if shouldExit {
		os.Exit(0)
	}
}
