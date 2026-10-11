export const GalaxyLoading = {
  props: { message: { type: String, default: 'Just a moment!' }, refresh: Boolean },
  methods: { reload() { location.reload() } },
  template: `<section class="gx-boot" role="status"><img class="gx-boot__logo" src="./assets/galaxy-icon.svg" width="160" height="160" alt="" /><h1>Galaxy</h1><div class="gx-boot__orbit" aria-hidden="true"></div><p>{{ message }}</p><button v-if="refresh" type="button" class="gx-icon-btn" aria-label="Refresh Galaxy" title="Refresh Galaxy" @click="reload"><i class="bi bi-arrow-clockwise" aria-hidden="true"></i></button></section>`,
}
