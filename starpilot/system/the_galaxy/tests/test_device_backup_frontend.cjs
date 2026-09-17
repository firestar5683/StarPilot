const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const base = path.resolve(__dirname, '../assets/mobile/js');
let accepted = false;
let downloadModels = false;
let restores = 0;
let backups = 0;
let prepareFails = false;
let spaceShortage = false;
let routeDeletes = 0;
let prepareResult = {success:true, filename:'starpilot-device-20260101-000000.zip', downloadUrl:'/api/device_backup/download/starpilot-device-20260101-000000.zip'};
let discards = 0;
let discardFails = false;
let restoreFails = false;
let finishFails = false;
let status = {stage:'idle'};
let confirmNoDownload = [];
const finishes = [];
const prompts = [];
const downloads = [];
const ctx = {
  GalaxySection: {}, GxNotice: {}, GalaxySelect: {}, VersionHistoryPicker: {},
  versionTitle: () => "", releaseVersions: commits => commits,
  downloadBlob: () => {},
  downloadUrl: (url, filename) => downloads.push([url, filename]),
  GalaxyConfirm: async options => {
    prompts.push(options);
    if (options.confirmLabel === 'Reboot Now') return confirmNoDownload.length ? confirmNoDownload.shift() : true;
    return options.dismissible === false ? downloadModels : accepted;
  },
  api: {
    restoreDevice: async () => {
      restores++;
      if (restoreFails) throw new Error('Invalid backup');
      return {success:true, message:'Settings restored', models:[{key:'a', standard:true, lab:false}]};
    },
    rebootAfterDeviceRestore: async download => {
      finishes.push(download);
      if (finishFails) throw new Error('Network unavailable');
      return {success:true, stage:download ? 'downloading' : 'rebooting', message:'Finishing restore'};
    },
    deviceRestoreStatus: async () => status,
    prepareDeviceBackup: async () => {
      backups++;
      if (spaceShortage) {
        spaceShortage = false;
        throw new Error('Not enough free space to build the backup: it needs about 3.0 GB but only 0.5 GB is free.');
      }
      if (prepareFails) throw new Error('Not enough space');
      return prepareResult;
    },
    deleteAllRoutes: async () => {
      routeDeletes++;
      return {message:'All local driving routes deleted.'};
    },
    discardDeviceRecovery: async () => {
      discards++;
      if (discardFails) throw new Error('Recovery files are locked');
      return {success:true, message:'Interrupted restore data was discarded.'};
    },
  },
};
vm.createContext(ctx);
const source = fs.readFileSync(path.join(base, 'views/SystemTools.js'), 'utf8')
  .replace(/^import[^\n]+\n/gm, '').replace('export const SystemTools', 'const SystemTools');
vm.runInContext(source + '\nthis.view = SystemTools;', ctx);
(async () => {
  const view = {...ctx.view.data(), ...ctx.view.methods, loadProfiles: async () => {}};
  const event = () => ({target:{files:[{name:'backup.zip'}], value:'backup.zip'}});
  await view.onDeviceRestoreFile(event());
  assert.equal(restores, 0, 'cancel before restore must not upload');
  accepted = true;
  view.isOnroad = true;
  await view.onDeviceRestoreFile(event());
  prepareFails = true;
  await view.backupDevice();
  assert.equal(restores, 0);
  assert.equal(backups, 0);
  view.isOnroad = false;
  await view.onDeviceRestoreFile(event());
  assert.deepEqual(finishes, [false], 'secondary action must reboot without downloading');
  assert.equal(prompts.at(-2).confirmLabel, 'Download Models and Reboot');
  assert.equal(prompts.at(-2).cancelLabel, 'Reboot Without Downloading');
  assert.equal(prompts.at(-2).dismissible, false, 'no Later/backdrop dismissal');
  assert.equal(prompts.at(-1).confirmLabel, 'Reboot Now', 'rebooting without downloads needs its own confirmation');
  assert.equal(prompts.at(-1).dismissible, false);
  confirmNoDownload = [false, true];
  view.deviceRestoreReady = true;
  const beforeBack = prompts.length;
  await view.rebootAfterRestore();
  assert.deepEqual(prompts.slice(beforeBack).map(prompt => prompt.confirmLabel),
    ['Download Models and Reboot', 'Reboot Now', 'Download Models and Reboot', 'Reboot Now'], 'Back returns to the choice');
  assert.deepEqual(finishes, [false, false]);
  assert.equal(view.deviceRestoreReady, false);
  downloadModels = true;
  await view.onDeviceRestoreFile(event());
  assert.deepEqual(finishes, [false, false, true]);
  assert.equal(view.deviceBackupBusy, 'models', 'poll until model downloads finish');
  status = {stage:'error', message:'Model unavailable', models:[{key:'a'}]};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRestoreReady, true);
  assert.equal(view.deviceBackupError, true);
  assert.equal(view.deviceBackupBusy, '');
  view.isOnroad = true;
  await view.rebootAfterRestore();
  assert.equal(finishes.length, 3);
  view.isOnroad = false;
  finishFails = true;
  await view.rebootAfterRestore();
  assert.equal(view.deviceRestoreReady, true, 'connection failure can be retried');
  assert.match(view.deviceBackupMessage, /final step could not be confirmed/);
  finishFails = false;
  downloadModels = false;
  await view.rebootAfterRestore();
  assert.equal(finishes.at(-1), false);
  restoreFails = true;
  const promptCount = prompts.length;
  const finishCount = finishes.length;
  await view.onDeviceRestoreFile(event());
  assert.equal(prompts.length, promptCount + 1, 'failed restore must not offer final choices');
  assert.equal(finishes.length, finishCount);
  await view.backupDevice();
  assert.equal(view.deviceBackupMessage, 'Not enough space');
  // A successful prepare streams the file by URL instead of buffering a JS blob.
  prepareFails = false;
  const downloadCount = downloads.length;
  await view.backupDevice();
  assert.equal(downloads.length, downloadCount + 1, 'successful backup must navigate to the download URL');
  assert.equal(downloads.at(-1)[0], prepareResult.downloadUrl);
  assert.equal(downloads.at(-1)[1], prepareResult.filename);
  assert.match(view.deviceBackupMessage, /Download started/);
  // A prepare response that reports failure is surfaced, not downloaded.
  prepareResult = {success:false, message:'No space for the backup'};
  await view.backupDevice();
  assert.equal(downloads.length, downloadCount + 1);
  assert.equal(view.deviceBackupMessage, 'No space for the backup');
  prepareResult = {success:true, filename:'starpilot-device-20260101-000000.zip', downloadUrl:'/api/device_backup/download/starpilot-device-20260101-000000.zip'};
  // A shortage of disk space offers to delete routes, then retries the backup automatically.
  const beforeSpaceBackups = backups;
  const beforeRoutes = routeDeletes;
  const beforeSpaceDownloads = downloads.length;
  spaceShortage = true;
  await view.backupDevice();
  assert.equal(routeDeletes, beforeRoutes + 1, 'a space shortage must offer to delete routes');
  assert.equal(backups, beforeSpaceBackups + 2, 'the backup is retried after route cleanup');
  assert.equal(downloads.length, beforeSpaceDownloads + 1, 'the retry streams the finished backup');
  assert.equal(prompts.at(-1).confirmLabel, 'Delete Routes and Retry');
  // A stopped, failed rollback exposes a discard action that unblocks backup/restore.
  status = {stage:'restore_error', message:'could not be fully rolled back', recoveryPending:true};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRecoveryPending, true);
  discardFails = true;
  await view.discardDeviceRecovery();
  assert.equal(discards, 1);
  assert.equal(view.deviceBackupError, true);
  assert.equal(view.deviceRecoveryPending, true, 'a failed discard keeps the action available');
  discardFails = false;
  await view.discardDeviceRecovery();
  assert.equal(view.deviceRecoveryPending, false);
  assert.equal(view.deviceBackupError, false);
  assert.match(view.deviceBackupMessage, /discarded/);
  // Recovery that is still waiting for park must not advertise the discard action.
  status = {stage:'restore_error', message:'waiting for park', recoveryPending:false};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRecoveryPending, false);
  // Page-load reports: finished restore, automatic rollback, pending or failed rollback.
  for (const [stage, error] of [['complete', false], ['rolled_back', false], ['restore_error', true]]) {
    const before = prompts.length;
    status = {stage, message:`${stage} message`};
    await view.loadDeviceRestoreStatus({prompt:true});
    assert.equal(view.deviceBackupMessage, `${stage} message`);
    assert.equal(view.deviceBackupError, error, `${stage} error styling`);
    assert.equal(view.deviceRestoreReady, false, `${stage} must not offer the reboot choice`);
    assert.equal(view.deviceRecoveryPending, false, `${stage} must not offer discard`);
    assert.equal(view.deviceBackupBusy, '');
    assert.equal(prompts.length, before, `${stage} must not prompt`);
  }
  // A reload mid-restore keeps the stage tracked so the poll resumes and still offers the reboot choice.
  status = {stage:'restoring', message:'Restoring backup...'};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRestoreStage, 'restoring');
  status = {stage:'awaiting_choice', message:'Restored 2 settings.', models:[]};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRestoreStage, 'awaiting_choice');
  assert.equal(view.deviceRestoreReady, true);
  status = {stage:'idle'};
  await view.loadDeviceRestoreStatus();
  assert.equal(view.deviceRestoreStage, 'idle');
  assert.equal(view.deviceRestoreReady, false);
  const section = ctx.view.template.split('title="Backup & Restore"')[1].split('</GalaxySection>')[0];
  assert.match(section, /@click="backupDevice"/);
  assert.match(section, /@change="onDeviceRestoreFile"/);
  assert.match(section, /v-if="deviceRecoveryPending"[^>]*@click="discardDeviceRecovery"/);
  assert.ok(!section.includes('href="/device_backup"'));
  const calls = [];
  const network = {FormData, fetch:async (url, options) => {calls.push({url, options}); return {ok:true, json:async()=>({success:true})};}};
  vm.createContext(network);
  vm.runInContext(fs.readFileSync(path.join(base, 'api.js'), 'utf8').replace(/export /g, '') + '\nthis.client=api;', network);
  const zip = new Blob(['zip']);
  await network.client.restoreDevice(zip);
  assert.equal(calls[0].url, '/api/device_backup/restore');
  assert.equal(calls[0].options.body, zip, 'raw body so the server streams it to /data');
  assert.equal(calls[0].options.headers['Content-Type'], 'application/zip');
  await network.client.prepareDeviceBackup();
  assert.equal(calls[1].url, '/api/device_backup/download');
  assert.equal(calls[1].options.method, 'POST');
  await network.client.rebootAfterDeviceRestore(true);
  assert.equal(calls[2].url, '/api/device_backup/reboot');
  assert.deepEqual(JSON.parse(calls[2].options.body), {downloadModels:true});
  await network.client.rebootAfterDeviceRestore(false);
  assert.deepEqual(JSON.parse(calls[3].options.body), {downloadModels:false});
  await network.client.discardDeviceRecovery();
  assert.equal(calls[4].url, '/api/device_backup/recovery');
  assert.equal(calls[4].options.method, 'DELETE');
  assert.deepEqual(JSON.parse(calls[4].options.body), {confirm:true});
  const modalSource = fs.readFileSync(path.join(base,'components/GalaxyModal.js'),'utf8');
  assert.match(modalSource, /@click.self="dismissible && cancel\(\)"/);
  console.log('Inline restore choices, streaming backup, discard recovery, confirmed reboot paths, progress polling, retry, guards and raw upload passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
