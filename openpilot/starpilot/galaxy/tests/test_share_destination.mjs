import test from 'node:test'
import assert from 'node:assert/strict'
import { parseSharedDestination as parse } from '../web/js/share-destination.js'
for (const text of ['https://maps.google.com/@12.3,-45.6,15z', 'https://maps.google.com/?q=12.3,-45.6',
  'geo:12.3,-45.6(Home)', 'google.navigation:q=12.3,-45.6', 'https://maps.google.com/?daddr=12.3,-45.6',
  'https://maps.google.com/@1,2,15z/data=!3d12.3!4d-45.6']) {
  test(text, () => { const { destination } = parse(text); assert.equal(destination.latitude, 12.3); assert.equal(destination.longitude, -45.6) })
}
test('address search', () => assert.equal(parse('geo:0,0?q=10+Main+Street').query, '10 Main Street'))
test('invalid coordinate does not route', () => assert.equal(parse('geo:123,456').destination, undefined))
test('encoded coordinates', () => assert.equal(parse('https://maps.google.com/?q=12.3%2C-45.6').destination.longitude, -45.6))
