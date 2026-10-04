export function createRouteLeave(port) {
  let current = port.read()
  let guard = null
  let restoring = null
  let approved = null
  let generation = 0
  const commit = () => { current = port.read(); port.show() }
  const ask = (proceed) => {
    const request = ++generation
    const once = () => { if (request === generation) { generation++; proceed() } }
    if (guard) guard(once)
    else once()
  }
  return {
    setGuard(value) { guard = value },
    navigate(path, before = null) {
      if (path === current.path && !before) return
      ask(() => {
        if (before) before()
        if (path !== current.path) { port.push(path, current.index + 1); commit() }
      })
    },
    back() {
      ask(() => {
        if (current.index > 0) { approved = { index: current.index - 1 }; port.go(-1) }
        else if (current.path !== "/") { port.replace("/", 0); commit() }
      })
    },
    changed() {
      let target = port.read()
      if (restoring) {
        if (target.path === current.path && target.index === current.index) {
          const move = restoring
          restoring = null
          ask(() => { approved = move.target; port.go(move.delta) })
        }
        return
      }
      if (approved && target.index === approved.index && (!approved.path || target.path === approved.path)) {
        approved = null
        commit()
        return
      }
      if (target.path === current.path && target.index === current.index) return
      if (target.index === null || target.index === current.index) {
        port.replace(target.path, current.index + 1)
        target = port.read()
      }
      const delta = target.index - current.index
      if (delta === 0) {
        port.replace(current.path, current.index)
        ask(() => { port.replace(target.path, target.index); commit() })
      } else {
        restoring = { target, delta }
        port.go(-delta)
      }
    },
  }
}
