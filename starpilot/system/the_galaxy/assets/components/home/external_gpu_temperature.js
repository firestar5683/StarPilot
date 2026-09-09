// Shared by Arrow and Vue. Only consumes modeld's read-only telemetry API.
export class ExternalGpuTemperature extends HTMLElement {
  connectedCallback() {
    this.textContent = "--";
    const generation = this.generation = (this.generation || 0) + 1;
    const poll = async () => {
      const start = performance.now();
      const controller = this.controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 1000);
      try {
        const response = await fetch("/api/vitals/external-gpu", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Telemetry unavailable");
        const data = await response.json();
        if (!this.isConnected || generation !== this.generation) return;
        window.dispatchEvent(new CustomEvent("egpu-vitals-sample", {detail: {data, start}}));
        // Deduct the entire request latency; never extend server sample life.
        const remaining = Math.min(3000, data.maxAgeMs) - (performance.now() - start);
        clearTimeout(this.expiry);
        if (typeof data.tempC === "number" && Number.isFinite(data.tempC) && data.tempC > 0
            && typeof data.maxAgeMs === "number" && Number.isFinite(remaining) && remaining > 0) {
          this.textContent = `${Math.round(data.tempC)}°C`;
          this.expiry = setTimeout(() => { this.textContent = "--"; }, remaining);
        } else {
          this.textContent = "--";
        }
      } catch (_) {
        // Request failure does not invalidate a still-fresh sample.
        // Its independent expiry still clears it at the original deadline.
      } finally {
        clearTimeout(timeout);
        if (this.isConnected && generation === this.generation) this.pollTimer = setTimeout(poll, 250);
      }
    };
    poll();
  }

  disconnectedCallback() {
    ++this.generation;
    clearTimeout(this.pollTimer);
    clearTimeout(this.expiry);
    this.controller?.abort();
    this.textContent = "--";
  }
}

if (!customElements.get("external-gpu-temperature")) {
  customElements.define("external-gpu-temperature", ExternalGpuTemperature);
}
