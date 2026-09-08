import { PersonalityProfiles } from "./PersonalityProfiles.js"
import { GalaxyToggleCard } from "./GalaxyToggleCard.js"
import { hasChildParams, isGroupParam, isParamEnabledForChildren } from "../params.js"

export const SettingTree = {
  name: "SettingTree",
  components: { GalaxyToggleCard, PersonalityProfiles },
  props: {
    params: { type: Array, required: true },
    parentKey: { default: null },
    depth: { type: Number, default: 0 },
    values: { type: Object, required: true },
    expanded: { type: Object, default: () => ({}) },
    lockReason: { type: Function, default: () => "" },
  },
  emits: ["change", "manage"],
  computed: {
    children() {
      return this.params.filter((p) => (p.parent_key || null) === this.parentKey)
    },
  },
  methods: {
    enabledForChildren(p) { return isParamEnabledForChildren(p, this.values) },
    isParent(p) { return hasChildParams(this.params, p.key) },
    isGroup(p) { return isGroupParam(p) },
    isExpanded(p) { return !!this.expanded[p.key] },
    showChildren(p) { return this.isParent(p) && this.enabledForChildren(p) && this.isExpanded(p) },
    manageable(p) { return this.isParent(p) && this.enabledForChildren(p) },
    manageOpen(p) { return this.isParent(p) && this.enabledForChildren(p) && this.isExpanded(p) },
  },
  template: `
    <template v-for="p in children" :key="p.key">
      <PersonalityProfiles v-if="p.key === 'CustomPersonalities'" :manage-open="isExpanded(p)" @manage="$emit('manage', p.key)" @change="$emit('change', $event)" />
      <div v-else class="gx-tree-node" :class="{ 'gx-tree-node--child': depth > 0 }" :style="'--gx-depth:' + depth">
        <GalaxyToggleCard :param="p" :value="values[p.key]" :values="values" :locked="lockReason(p) !== ''"
          :manageable="manageable(p)" :manage-open="manageOpen(p)"
          @change="$emit('change', $event)" @manage="$emit('manage', $event)" />
      </div>
      <transition name="gx-collapse">
        <div v-if="p.key !== 'CustomPersonalities' && showChildren(p)" class="gx-tree-children">
          <SettingTree :params="params" :parent-key="p.key" :depth="depth + 1"
            :values="values" :expanded="expanded" :lock-reason="lockReason"
            @change="$emit('change', $event)" @manage="$emit('manage', $event)" />
        </div>
      </transition>
    </template>
  `,
}
