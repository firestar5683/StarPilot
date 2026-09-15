// Reuses the temperature widget's request: no extra polling or hardware reads.
export class ExternalGpuMemory extends HTMLElement {
  connectedCallback() {
    this.textContent = "--";
    this.title = "Allocated/cached and driver-reserved VRAM, out of physical capacity";
    this.listener = ({detail: {data, start}}) => {
      if (!this.isConnected) return;
      clearTimeout(this.expiry);
      const remaining = Math.min(3000, data.memoryMaxAgeMs) - (performance.now() - start);
      const used = data.memoryUsedBytes, total = data.memoryTotalBytes;
      if (Number.isSafeInteger(used) && Number.isSafeInteger(total) && used >= 0 && total > 0 && used <= total
          && typeof data.memoryMaxAgeMs === "number" && Number.isFinite(remaining) && remaining > 0) {
        this.textContent = `${(used / 2**30).toFixed(1)}/${(total / 2**30).toFixed(1)} GiB (${Math.round(100 * used / total)}%)`;
        this.expiry = setTimeout(() => { this.textContent = "--"; }, remaining);
      } else {
        this.textContent = "--";
      }
    };
    window.addEventListener("egpu-vitals-sample", this.listener);
  }
  disconnectedCallback() {
    window.removeEventListener("egpu-vitals-sample", this.listener);
    clearTimeout(this.expiry);
    this.textContent = "--";
  }
}
if (!customElements.get("external-gpu-memory")) customElements.define("external-gpu-memory", ExternalGpuMemory);
