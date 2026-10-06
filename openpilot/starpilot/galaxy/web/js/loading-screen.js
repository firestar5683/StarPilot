export const GalaxyLoading = {
  props: { message: { type: String, default: 'Opening Galaxy…' } },
  template: `<section class="gx-boot" role="status"><img class="gx-boot__logo" src="./assets/galaxy-icon.svg" width="160" height="160" alt="" /><h1>Galaxy</h1><div class="gx-boot__orbit" aria-hidden="true"></div><p>{{ message }}</p></section>`,
}
