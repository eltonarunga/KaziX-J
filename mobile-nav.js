(function () {
  function setExpanded(wrapper, isOpen) {
    wrapper.classList.toggle("open", isOpen);
    var toggle = wrapper.querySelector(".mobile-nav-more-toggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
  }

  function closeAll(openMenus, except) {
    openMenus.forEach(function (wrapper) {
      if (wrapper !== except) {
        setExpanded(wrapper, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var moreMenus = Array.from(document.querySelectorAll(".mobile-nav-more"));
    if (!moreMenus.length) {
      return;
    }

    moreMenus.forEach(function (wrapper, index) {
      var toggle = wrapper.querySelector(".mobile-nav-more-toggle");
      var drawer = wrapper.querySelector(".mobile-nav-drawer");
      if (!toggle || !drawer) {
        return;
      }

      var drawerId = drawer.id || "mobile-nav-drawer-" + (index + 1);
      drawer.id = drawerId;
      toggle.setAttribute("aria-controls", drawerId);
      toggle.setAttribute("aria-expanded", "false");

      toggle.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();

        var shouldOpen = !wrapper.classList.contains("open");
        closeAll(moreMenus, wrapper);
        setExpanded(wrapper, shouldOpen);
      });
    });

    document.addEventListener("click", function (event) {
      if (!event.target.closest(".mobile-nav-more")) {
        closeAll(moreMenus);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeAll(moreMenus);
      }
    });
  });
})();
