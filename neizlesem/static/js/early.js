/* Sayfa çizilmeden önce çalışır: JS sınıfını koyar; aramadan gelindiyse "ışıklar yanar" girişini hazırlar. */
(function () {
  var root = document.documentElement;
  root.classList.add("js");
  try {
    if (sessionStorage.getItem("ni-isik") === "1") {
      sessionStorage.removeItem("ni-isik");
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        root.classList.add("with-lights");
      }
    }
  } catch (e) { /* gizli sekme vb. */ }
})();
