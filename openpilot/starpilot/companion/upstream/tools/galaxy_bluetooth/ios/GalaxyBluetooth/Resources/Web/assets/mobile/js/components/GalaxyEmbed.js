// Single source of truth for page-in-page embeds of the classic Galaxy SPA.
// Ideally, implement new tools Vue based instead of Arrow.
export const GalaxyEmbed = {
  name: "GalaxyEmbed",
  props: {
    src: { type: String, required: true },
    title: { type: String, default: "Tool" },
    // When true, injects a bridge that forwards the classic page's internal
    // navigation to the mobile app (which opens it as a proper ToolEmbed page).
    forwardNav: { type: Boolean, default: false },
  },
  data() {
    return {
      embedStyle: `
        #sidebar, #sidebar_shell, #sidebarUnderlay { display: none !important; }
        #menu_button { display: none !important; }
        .content { margin-left: 0 !important; }
        body { padding-left: 0 !important; }
      `,
    }
  },
  computed: {
    frameSrc() {
      const base = this.src
      return base + (base.includes("?") ? "&" : "?") + "embedded=1"
    },
  },
  methods: {
    injectEmbedStyles() {
      const frame = this.$refs.frame
      if (!frame) return
      try {
        const doc = frame.contentDocument || frame.contentWindow?.document
        if (!doc || !doc.head) return
        let style = doc.getElementById("gx-embed-hide-sidebar")
        if (!style) {
          style = doc.createElement("style")
          style.id = "gx-embed-hide-sidebar"
          doc.head.appendChild(style)
        }
        style.textContent = this.embedStyle

        if (!this.forwardNav) return
        let bridge = doc.getElementById("gx-embed-nav-bridge")
        if (!bridge) {
          bridge = doc.createElement("script")
          bridge.id = "gx-embed-nav-bridge"
          bridge.textContent = `(() => {
            const post = () => {
              if (window.self === window.top) return
              const params = new URLSearchParams(window.location.search)
              params.delete("embedded")
              const qs = params.toString()
              window.parent.postMessage({ source: "galaxy-embed", path: window.location.pathname + (qs ? "?" + qs : "") }, "*")
            }
            const patch = (type) => {
              const orig = history[type]
              history[type] = function () { const r = orig.apply(this, arguments); post(); return r }
            }
            patch("pushState")
            patch("replaceState")
            window.addEventListener("popstate", post)
          })()`
          doc.head.appendChild(bridge)
        }
      } catch (e) {
      }
    },
  },
  mounted() {
    this.$refs.frame?.addEventListener("load", () => this.injectEmbedStyles())
  },
  template: `
    <div class="gx-embed">
      <iframe ref="frame" :src="frameSrc" class="gx-embed__frame" frameborder="0"
        allow="clipboard-read; clipboard-write" :title="title"></iframe>
    </div>
  `,
}
