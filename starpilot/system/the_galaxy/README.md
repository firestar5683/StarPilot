# The Galaxy

**The Galaxy** is a lightweight web-based interface for managing your device. It allows you to adjust settings remotely, view video streams, and download logs—all from your browser.

---

# Architecture

The Galaxy has two main components:  
- A **Python Flask API**  
- A **frontend built with Arrow.js** (a minimal reactive framework)

Because the frontend uses native ES modules, there's no need for a build step or Node.js tooling.

## API

The API is simple and defined in `the_galaxy.py`. It exposes a handful of JSON-based endpoints via standard Flask routes:

- Get and update settings  
- Fetch error logs  
- List recorded routes  
- Load a specific route and video stream (ported from Fleet Manager)  
- Save a navigation destination (triggers OpenPilot navigation)

## Web App

The frontend is built using [Arrow.js](https://www.arrow-js.com), chosen for its simplicity and native module support (no bundlers required). It includes the following main components:

- **Error Logs**
- **Navigation**
- **Routes**
- **Settings**

It also includes some layout-related components:

- `"router"` – for dynamic view switching
- `"sidebar"` – for navigation

---

# Development Guide

## Adding a New Page

To add a new page:

1. **Create the component**  
   Add a new file in the `components/` directory.

2. **Register the route**  
   Add your route to `router.js`. The router uses a simple list of route definitions:

    ```js
    let routes = [
      createRoute("errorLogs", "/error_logs", ErrorLogs),
      createRoute("navdestination", "/navigation", NavDestination),
      createRoute("root", "/", Home),
      createRoute("route", "/routes/:routeDate", RecordedRoute),
      createRoute("routes", "/routes", RecordedRoutes),
      createRoute("settings", "/settings/:section/:subsection?", SettingsView),
      createRoute("NAME", "/URL_PATH", ComponentName), <-- Insert your component here
    ];
    ```

3. **Add to sidebar**  
   Modify `sidebar.js` to include your new route:

    ```js
    const MenuItems = {
      ...
      navigation: [
        {
          name: "Set destination",
          link: "/navigation",
          icon: "bi-globe-americas",
        },
        {
          name: "Sidebar title", <-- Add your new page here
          link: "/URL_PATH", <-- Same url as in router.js
          icon: "" <-- Add an icon here (Bootstrap icons are used, see https://icons.getbootstrap.com/
        },
      ],
      ...
    }
    ```

4. **Create the component**  
   Here's a simple example component:

    ```js
    import { html, reactive } from "https://esm.sh/@arrow-js/core"

    export function MyComponent() {
      const state = reactive({
        message: "Hello from MyComponent"
      })

      return html`
        <div>
          <h1>${state.message}</h1>
        </div>
      `
    }
    ```

---

# Running The Galaxy

## On your desktop

Galaxy is a Flask app, so previewing it means opening a browser on your own machine.
Nothing needs to be pushed to a device.

```bash
./dev galaxy --live
```

That builds the isolated host runtime under `.host_runtime/<platform>/` on first run
(several minutes -- it compiles `params_pyx`, `transformations`, and the msgq/visionipc
extensions), then serves <http://127.0.0.1:8083/> with reload enabled. Later runs start
immediately. `scripts/galaxy_live.sh [--sync] [port]` is the same thing and is fine to
call directly.

While it is up:

- Backend edits (`the_galaxy.py`, `utilities.py`, ...) restart the server in place, and
  tracebacks print in the terminal you launched from.
- Frontend edits (`assets/components/`, `assets/mobile/`, `templates/index.html`) are
  served straight off disk, but `assets/service-worker.js` will hand you a stale bundle
  on a plain refresh. Use a hard reload, or keep DevTools open with "Disable cache" on.
- Only `starpilot/system/the_galaxy/` is live -- it is symlinked into the host runtime.
  Changes anywhere else (`starpilot/common/`, `system/hardware/`, cereal schemas) need
  `scripts/galaxy_live.sh --sync` to be copied across.
- The mobile Vue app under `assets/mobile/` is served from the same port. Use your
  browser's device emulation rather than a second launcher.
- Only one live session runs at a time. A second `./dev galaxy --live` (or a direct
  `scripts/galaxy_live.sh`) refuses to start until the first is stopped, and snapshot
  `./dev galaxy` also refuses while live is up, since it would otherwise serve the live
  working tree. When a live session ends, the next host sync drops the symlink, so
  `./dev galaxy` is a true snapshot again.

### Snapshot instead of live

```bash
./dev galaxy
```

Runs the code as of when you started it, with the reloader off, on a free port picked
from 4600-8022 (`pick_free_galaxy_port()` keeps Galaxy below the range desktop ZMQ
hashes replay service names into). Use it when you want a stable server that ignores
whatever you are editing. It refuses to start while a `--live` session is running, so
stop that first.

### With replayed data

```bash
./onroad --replay-only --galaxy --demo     # Galaxy only
./onroad --galaxy <route>                  # Galaxy plus a desktop raylib UI
```

Starts replay alongside Galaxy so panels that read live streams have something to show.
It blocks replay's logged `customReserved9` stream so Galaxy owns the Testing Grounds
publisher, waits on `/api/galaxy/status`, then prints the URL.

`--galaxy` does not replace the UI selection: unless you pass `--replay-only`, a desktop
raylib UI launches as well, picked from the route's logged device type. Use
`--replay-only` when you only want the browser.

### Environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `SP_GALAXY_PORT` | `8082` on device, `8083` off | On-device must stay 8082 to match Galaxy FRP routing |
| `SP_GALAXY_HOST` | `0.0.0.0` | |
| `SP_GALAXY_DEBUG` | `0` on device, `1` off | Flask debug mode |
| `SP_GALAXY_RELOAD` | follows `SP_GALAXY_DEBUG` off device, always off on device | The Flask auto-reloader. `./dev galaxy` pins it to `0` for a stable snapshot; `galaxy_live.sh` pins it to `1` |
| `SP_GALAXY_DIR` | `/data/galaxy` on device, `~/.comma/starpilot/data/galaxy` off | Galaxy's state directory |

### What does not work off-device

These degrade rather than crash, so they are expected, not bugs:

- The driver-camera preview needs `camerad`; without it the endpoint returns nothing.
- Endpoints backed by `SubMaster`/`sub_sock` (plots, CAN, car state) time out with no
  publisher. Use `./onroad --galaxy` if you need them populated.
- `/data/...` paths resolve under `~/.comma/starpilot/` via `Paths.comma_home()`.
- Car make/model falls back to a mock when no car is fingerprinted.
