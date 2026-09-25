import assert from 'node:assert/strict'
import { validOperation, formatBytes, MapOperationsPanel } from '../web/js/map-operations.js'
const generation = 'a'.repeat(64)
const status = { schemaVersion: 1, ownerSession: 'owner', operationId: 'owner:1', state: 'completed', regionToken: 'us_state.Oklahoma',
  bounds: [35, -98, 35.25, -97.75], completedGroups: 1, totalGroups: 1, transferredBytes: 256, transferBudgetBytes: 1024,
  preparedGeneration: generation, selectedGeneration: generation, errorCode: null, selectedForNextShadowStart: true,
  selectedSnapshot: { generation, storedBytes: 1024, tileCount: 1, bounds: [35, -98, 35.25, -97.75] } }
assert.equal(validOperation(status), true)
for (const info of [undefined, null, { ...status.selectedSnapshot, storedBytes: 0 },
                    { ...status.selectedSnapshot, tileCount: 0 }, { ...status.selectedSnapshot, generation: 'b'.repeat(64) },
                    { ...status.selectedSnapshot, bounds: null }, { ...status.selectedSnapshot, storedBytes: Number.NaN }]) {
  assert.equal(validOperation({ ...status, selectedSnapshot: info }), false)
}
assert.equal(formatBytes(512), '512 B')
assert.equal(formatBytes(1024), '1.0 KiB')
assert.equal(formatBytes(2 * 1024 ** 2), '2.0 MiB')
assert.equal(formatBytes(2 * 1024 ** 3), '2.0 GiB')
assert.match(MapOperationsPanel.template, /Offline map database/)
assert.match(MapOperationsPanel.template, /selectedSnapshot.storedBytes/)
assert.match(MapOperationsPanel.template, /selectedSnapshot.tileCount/)
assert.doesNotMatch(MapOperationsPanel.template, /Download complete\. This map will be used/)
console.log('PASS: nonempty package identity required for completed projection; actual size and units rendered')
