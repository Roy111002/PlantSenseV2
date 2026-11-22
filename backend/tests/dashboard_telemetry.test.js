// Exercise the real refresh flow against newer telemetry and an older AI result.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    value: id === "deviceId" ? "test-device" : "temperature_c",
    textContent: "", innerHTML: "", className: "", style: {},
    classList: {toggle() {}}, addEventListener() {}, appendChild() {},
    getBoundingClientRect: () => ({width: 400, height: 190}),
    getContext: () => ({scale() {}, clearRect() {}}),
  });
  return elements.get(id);
}
let telemetry = {
  created_at: new Date().toISOString(),
  sensor_data: {temperature_c: 31, light_lux: 0},
  actuator_state: {pump: "OFF", grow_light: "ON"},
};
let imageInfo={image_id:7,received_at:new Date().toISOString()};
const imageLoads=[];
const imageInstances=[];
const context = vm.createContext({
  AbortController, setTimeout, clearTimeout,
  document: {getElementById: element},
  window: {addEventListener() {}, devicePixelRatio: 1},
  Image: class {constructor(){imageInstances.push(this);} set src(value){this.url=value;imageLoads.push(value);}}, setInterval() {},
  fetch: async (url) => ({ok: true, json: async () => {
    if (url.includes("latest-data")) return telemetry;
    if (url.includes("latest-image-info")) return imageInfo;
    if (url.includes("history")) return {items: []};
    if (url.includes("/latest?")) return {
      created_at: "2020-01-01T00:00:00+00:00", ai_status: "completed",
      result: {sensor_data: {temperature_c: 99},
        actuator_state: {pump: "ON", grow_light: "OFF"},
        analysis: {vlm: {disease: "older diagnosis"}}},
    };
    return {status: "ok"};
  }}),
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../static/js/dashboard.js"), "utf8"), context);
(async () => {
  await new Promise(setImmediate);
  assert.match(element("metrics").innerHTML, /31\.0/);
  assert.doesNotMatch(element("metrics").innerHTML, /99\.0|STALE/);
  assert.match(element("metrics").innerHTML, /Light intensity/);
  assert.equal(element("pumpState").textContent, "OFF");
  assert.equal(element("lightState").textContent, "ON");
  assert.match(element("diagnosisContent").innerHTML, /older diagnosis/);
  assert.match(element("imageTimestamp").textContent,/Image #7/);
  assert.equal(imageLoads.length,1);
  await vm.runInContext("refresh()",context);
  assert.equal(imageLoads.length,1,"Unchanged image should not reload every poll");
  imageInfo={image_id:8,received_at:new Date().toISOString()};
  await vm.runInContext("refresh()",context);
  assert.equal(imageLoads.length,2);
  let appended=0;
  element("plantImageWrap").appendChild=()=>{appended++;};
  imageInstances[0].onload();
  assert.equal(appended,0,"Late response for older image must not replace newer frame");
  imageInstances[1].onload();
  assert.equal(appended,1);
  imageInfo.received_at="2020-01-01T00:00:00+00:00";
  await vm.runInContext("refresh()",context);
  assert.match(element("imageTimestamp").textContent,/STALE/);
  telemetry = {...telemetry, sensor_data: {}};
  await vm.runInContext("refresh()", context);
  assert.match(element("metrics").innerHTML, /No sensor readings/);
  assert.doesNotMatch(element("metrics").innerHTML, /99\.0|31\.0/);
  telemetry.created_at = "2020-01-01T00:00:00+00:00";
  await vm.runInContext("refresh()", context);
  assert.equal(element("pumpState").textContent, "OFF (stale)");
  console.log("Dashboard telemetry regression checks passed");
})().catch(error => { console.error(error); process.exitCode = 1; });
