// SYNTHETIC API fixture on stdin; execute unchanged candidate ES module.
import {readFileSync} from 'node:fs';
const source = new URL('../assets/components/tools/model_metrics.js', import.meta.url);
const metrics = await import('data:text/javascript;base64,' + readFileSync(source).toString('base64'));
const model = JSON.parse(readFileSync(0, 'utf8'));
console.log(JSON.stringify({trackingStatus: metrics.trackingStatus(model), drivingMetrics: metrics.drivingMetrics(model)}));
