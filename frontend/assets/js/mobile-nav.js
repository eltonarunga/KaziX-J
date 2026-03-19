(function () {
  var OVERLAY_PAGE_SELECTORS = [".chat-messages", ".applicants-list"];

  function isScrollablePage() {
    return OVERLAY_PAGE_SELECTORS.some(function (selector) {
      return Boolean(document.querySelector(selector));
    });
  }

  function getFirstFocusable(drawer) {
    return drawer.querySelector(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
  }

  function createOverlay() {
    var overlay = document.createElement("button");
    overlay.type = "button";
    overlay.className = "mobile-nav-overlay";
    overlay.setAttribute("aria-label", "Close navigation menu");
    overlay.setAttribute("aria-hidden", "true");
    overlay.tabIndex = -1;
    document.body.appendChild(overlay);
    return overlay;
  }

  function setOverlayState(overlay, isOpen) {
    if (!overlay) {
      return;
    }
    overlay.classList.toggle("active", isOpen);
    overlay.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }

  function setExpanded(wrapper, isOpen, options) {
    options = options || {};
    var wasOpen = wrapper.classList.contains("open");
    if (!wasOpen && !isOpen) {
      return;
    }

    wrapper.classList.toggle("open", isOpen);
    var toggle = wrapper.querySelector(".mobile-nav-more-toggle");
    var drawer = wrapper.querySelector(".mobile-nav-drawer");

    if (toggle) {
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }
    if (drawer) {
      drawer.setAttribute("aria-hidden", isOpen ? "false" : "true");
    }

    if (isOpen && options.focusFirstLink && drawer) {
      var firstFocusable = getFirstFocusable(drawer);
      if (firstFocusable) {
        firstFocusable.focus();
      }
    }

    if (!isOpen && options.returnFocus && toggle) {
      toggle.focus();
    }
  }

  function closeAll(openMenus, except, options) {
    options = options || {};
    openMenus.forEach(function (wrapper) {
      if (wrapper !== except && wrapper.classList.contains("open")) {
        setExpanded(wrapper, false, { returnFocus: options.returnFocus });
      }
    });

    if (options.overlay) {
      var hasOpenMenu = openMenus.some(function (wrapper) {
        return wrapper.classList.contains("open");
      });
      setOverlayState(options.overlay, hasOpenMenu);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var moreMenus = Array.from(document.querySelectorAll(".mobile-nav-more"));
    if (!moreMenus.length) {
      return;
    }

    var overlay = isScrollablePage() ? createOverlay() : null;

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
      toggle.setAttribute("aria-label", "Open navigation menu");
      drawer.setAttribute("aria-hidden", "true");
      wrapper.classList.remove("open");

      toggle.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();

        var shouldOpen = !wrapper.classList.contains("open");

        closeAll(moreMenus, wrapper, { overlay: overlay });

        if (shouldOpen) {
          setExpanded(wrapper, true, { focusFirstLink: true });
        } else {
          setExpanded(wrapper, false, { returnFocus: true });
        }

        setOverlayState(overlay, shouldOpen);
      });
    });

    if (overlay) {
      overlay.addEventListener("pointerdown", function (event) {
        event.preventDefault();
        closeAll(moreMenus, null, { returnFocus: true, overlay: overlay });
      });
    }

    document.addEventListener("pointerdown", function (event) {
      var target = event.target;
      if (target.closest(".mobile-nav-drawer") || target.closest(".mobile-nav")) {
        return;
      }

      closeAll(moreMenus, null, { returnFocus: true, overlay: overlay });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeAll(moreMenus, null, { returnFocus: true, overlay: overlay });
      }
    });
  });
})();
