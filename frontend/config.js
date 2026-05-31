(function () {
  const protocol = window.location.protocol === "file:" ? "http:" : window.location.protocol;
  const hostname = window.location.hostname || "localhost";

  window.APP_CONFIG = window.APP_CONFIG || {};
  window.APP_CONFIG.geoserverWmsUrl =
    window.APP_CONFIG.geoserverWmsUrl ||
    `${protocol}//${hostname}:8080/geoserver/renewable_nz/wms`;
})();
