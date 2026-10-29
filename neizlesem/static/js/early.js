/* Sayfa çizilmeden önce çalışır: aramadan gelindiyse perde açılış animasyonunu hazırlar. */
(function () {
  try {
    if (sessionStorage.getItem("ni-perde") === "1") {
      sessionStorage.removeItem("ni-perde");
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        document.documentElement.classList.add("with-curtain");
      }
    }
  } catch (e) { /* gizli sekme vb. */ }
})();
