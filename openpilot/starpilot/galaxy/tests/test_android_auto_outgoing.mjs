import assert from "node:assert/strict";
import { test } from "node:test";
import { AndroidAutoFeed, AndroidAutoPage, validPairingStatus } from "../web/js/android-auto.js";
const car = { address: "AA:BB:CC:DD:EE:FF", name: "IONIQ 6", paired: true, connected: false, android_auto: false };
const pairing = {active: true, approved: false, receiver: null, prompt: null, devices: [car], discovering: true, state: "idle", error: ""};
test("plain Bluetooth saved car remains discoverable without an AA UUID", () => {
  assert.equal(validPairingStatus(pairing), true);
  assert.equal(validPairingStatus({...pairing, devices: [{...car, paired: "yes"}]}), false);
  assert.equal(validPairingStatus({...pairing, state: "unexpected"}), false);
});
test("select uses outgoing API without changing the selected AA receiver", async () => {
  const feed = new AndroidAutoFeed({publish() {}});
  feed.active = true; feed.setup = {parked: true, enabled: true}; feed.pairing = pairing;
  feed.selected = {address: "11:22:33:44:55:66", name: "Adapter"};
  let sent;
  feed.action = async (path, body) => {sent = {path, body}; return true;};
  assert.equal(await feed.selectDevice(car.address), true);
  assert.deepEqual(sent, {path: "./api/android-auto/pairing/select", body: {address: car.address}});
  assert.equal(feed.selected.name, "Adapter");
  assert.equal(await feed.selectDevice("00:00:00:00:00:00"), false);
  feed.pairing = {...pairing, state: "connecting"};
  assert.equal(await feed.selectDevice(car.address), false);
  feed.pairing = pairing; feed.runtime = {running: true};
  assert.equal(await feed.selectDevice(car.address), false);
});
test("search remains blocked during projection and code verification stays available", () => {
  const page = {pairingReason: "", runtime: {running: true}, feed: {action() {throw Error("unexpected request");}}};
  assert.equal(AndroidAutoPage.methods.startPairing.call(page), false);
});
