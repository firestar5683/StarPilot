// Numeric summaries get equal space instead of squeezing the section heading.
export const GxSummary = {
  props: { items: { type: Array, required: true } },
  template: `<dl class="gx-summary"><div v-for="item in items" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></div></dl>`,
}
