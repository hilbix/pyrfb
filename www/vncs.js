"use strict";

window.onscriptsload = function () { mkrfb(window.location.hostname, 443, '', 'vnc'+window.location.search.substr(1)); }

