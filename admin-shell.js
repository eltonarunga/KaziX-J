(function () {
  function buildTopnav() {
    var nav = document.createElement('nav');
    nav.className = 'topnav';
    nav.innerHTML = ''
      + '<a href="index.html" class="logo">Kazi<span>X</span></a>'
      + '<div class="topnav-right">'
      + '  <button class="notif-btn">!<span class="notif-dot"></span></button>'
      + '  <div class="user-chip"><div class="user-avatar">AD</div><span class="user-name">Admin Desk</span></div>'
      + '</div>';
    return nav;
  }

  function buildSidebar(activeKey) {
    var sidebar = document.createElement('aside');
    sidebar.className = 'sidebar';

    var adminLinks = [
      { key: 'disputes', label: 'Disputes', href: 'admin-disputes.html', icon: 'D', badge: '18' },
      { key: 'payments', label: 'Payments', href: 'admin-payments.html', icon: 'P' }
    ];

    var opsLinks = [
      { key: 'verifications', label: 'Verifications', href: 'admin-verifications.html', icon: 'K' },
      { key: 'users', label: 'Users', href: 'admin-users.html', icon: 'U' }
    ];

    function renderLinks(items) {
      return items.map(function (item) {
        var badge = item.badge ? '<span class="ni-badge">' + item.badge + '</span>' : '';
        return ''
          + '<a class="nav-item" data-nav="' + item.key + '" href="' + item.href + '">'
          + '<span class="ni-icon">' + item.icon + '</span>'
          + item.label
          + badge
          + '</a>';
      }).join('');
    }

    sidebar.innerHTML = ''
      + '<div class="sidebar-section">Admin</div>'
      + renderLinks(adminLinks)
      + '<div class="sidebar-section">Operations</div>'
      + renderLinks(opsLinks);

    var activeLink = sidebar.querySelector('[data-nav="' + activeKey + '"]');
    if (activeLink) {
      activeLink.classList.add('active');
    }

    return sidebar;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var main = document.querySelector('[data-admin-main]');
    if (!main) {
      return;
    }

    document.body.classList.add('app');
    var activeKey = document.body.getAttribute('data-admin-active') || '';

    if (!document.querySelector('.topnav')) {
      var nav = buildTopnav();
      document.body.insertBefore(nav, document.body.firstChild);
    }

    var shell = document.createElement('div');
    shell.className = 'app-shell';

    var sidebar = buildSidebar(activeKey);
    shell.appendChild(sidebar);
    shell.appendChild(main);

    var existingShell = document.querySelector('.app-shell');
    if (existingShell) {
      existingShell.replaceWith(shell);
    } else {
      var navEl = document.querySelector('.topnav');
      if (navEl) {
        document.body.insertBefore(shell, navEl.nextSibling);
      } else {
        document.body.insertBefore(shell, document.body.firstChild);
      }
    }
  });
})();
