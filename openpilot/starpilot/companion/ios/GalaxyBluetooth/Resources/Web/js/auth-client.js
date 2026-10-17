// Browser-only Galaxy session boundary; never persists passwords or tokens.
import { requestJson } from "./startup.js"

export class LocalAuth {
  constructor({ publish, fetcher = (...args) => fetch(...args) }) {
    this.publish = publish
    this.fetcher = fetcher
    this.generation = 0
    this.gatewayAccess = false
    this.localAccess = false
    this.mutationTail = Promise.resolve()
  }

  update(state, localAccess = false) {
    this.localAccess = localAccess
    this.publish({ ...state, localAccess })
  }

  mutate(operation) {
    const pending = this.mutationTail.then(operation)
    this.mutationTail = pending.then(() => {}, () => {})
    return pending
  }

  async check() {
    const generation = ++this.generation
    try {
      const result = await requestJson("./api/auth/session", { fetcher: this.fetcher })
      if (generation !== this.generation) return
      this.gatewayAccess = result.gatewayAccess === true
      this.publish({ gatewayAccess: this.gatewayAccess })
      if (result.state === "unavailable") this.update({ status: "unavailable", error: "Galaxy access is unavailable." })
      else if (result.state === "setup_required") this.update({ status: "setup_required", error: "Remote Galaxy access is not configured." })
      else if (result.state === "configured") this.update({ status: result.authenticated === true ? "authenticated" : this.gatewayAccess ? "gateway_login" : "login", error: "",
        ...(this.gatewayAccess ? { gatewayAccess: true } : {}) },
        result.authenticated === true && result.localAccess === true)
      else throw new Error("Invalid session state")
    } catch {
      if (generation === this.generation) this.update({ status: "unavailable", error: "Galaxy access could not be checked." })
    }
  }

  login(password) {
    if (this.localAccess || this.gatewayAccess) return Promise.resolve(false)
    const generation = ++this.generation
    return this.mutate(async () => {
      try {
        const response = await this.fetcher("./api/auth/login", {
          method: "POST", credentials: "same-origin", cache: "no-store",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }),
        })
        if (generation !== this.generation) return false
        if (!response.ok) {
          if (response.status === 429) this.update({ status: "login", error: "Try again shortly." })
          else if (response.status === 503) this.update({ status: "unavailable", error: "Galaxy access is unavailable." })
          else this.update({ status: "login", error: "Sign in failed." })
          return false
        }
        this.update({ status: "authenticated", error: "" })
        return true
      } catch {
        if (generation === this.generation) this.update({ status: "login", error: "Sign in could not be completed." })
        return false
      }
    })
  }

  logout() {
    if (this.localAccess || this.gatewayAccess) return Promise.resolve(false)
    const generation = ++this.generation
    return this.mutate(async () => {
      try {
        const response = await this.fetcher("./api/auth/logout", {
          method: "POST", credentials: "same-origin", cache: "no-store",
          headers: { "Content-Type": "application/json" }, body: "{}",
        })
        if (generation !== this.generation) return false
        if (response.status === 401 || response.status === 503) {
          this.update({ status: response.status === 503 ? "unavailable" : "login", error: "" })
          return false
        }
        if (!response.ok) throw new Error("Logout failed")
        this.update({ status: "login", error: "" })
        return true
      } catch {
        if (generation === this.generation) this.update({ status: "authenticated", error: "Sign out could not be completed." })
        return false
      }
    })
  }

  expired() {
    this.generation++
    if (this.localAccess || this.gatewayAccess) this.update({ status: "checking", error: "" })
    else this.update({ status: "login", error: "Your Galaxy session expired. Sign in again." })
  }
}
