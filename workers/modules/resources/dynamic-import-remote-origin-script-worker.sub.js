// Import a remote origin script.
const import_url =
    'https://{{domains[www1]}}:{{ports[https][0]}}/workers/modules/resources/export-on-load-script.js';
if ('DedicatedWorkerGlobalScope' in self &&
    self instanceof DedicatedWorkerGlobalScope) {
  import(import_url)
      .then(module => postMessage(module.importedModules))
      .catch(e => postMessage(['ERROR']));
} else if (
    'SharedWorkerGlobalScope' in self &&
    self instanceof SharedWorkerGlobalScope) {
  onconnect = e => {
    import(import_url)
        .then(module => e.ports[0].postMessage(module.importedModules))
        .catch(error => e.ports[0].postMessage(['ERROR']));
  };
}
