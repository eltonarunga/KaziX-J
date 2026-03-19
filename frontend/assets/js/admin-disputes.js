document.addEventListener('DOMContentLoaded', function () {
  var list = document.getElementById('disputeList');
  if (!list) {
    return;
  }

  var items = Array.prototype.slice.call(list.querySelectorAll('.list-item'));
  var emptyState = document.getElementById('emptyState');
  var searchInput = document.getElementById('searchInput');
  var sortSelect = document.getElementById('sortSelect');
  var filterButtons = Array.prototype.slice.call(document.querySelectorAll('[data-status-filter]'));

  var queueBadge = document.getElementById('queueBadge');

  var state = {
    status: 'open',
    query: '',
    sort: 'desc'
  };

  function statusLabel(status) {
    if (status === 'open') return 'Open';
    if (status === 'investigating') return 'Investigating';
    if (status === 'resolved') return 'Resolved';
    return status;
  }

  function updateQueueBadge() {
    if (!queueBadge) return;
    queueBadge.classList.remove('open', 'investigating', 'resolved');
    queueBadge.classList.add(state.status);
    queueBadge.textContent = statusLabel(state.status);
  }

  function parseDate(value) {
    if (!value) return 0;
    var date = new Date(value + 'T00:00:00');
    return isNaN(date.getTime()) ? 0 : date.getTime();
  }

  function matchesSearch(item, query) {
    if (!query) return true;
    var ref = (item.getAttribute('data-ref') || '').toLowerCase();
    var fundi = (item.getAttribute('data-fundi') || '').toLowerCase();
    return (ref + ' ' + fundi).indexOf(query) !== -1;
  }

  function applyFilters() {
    var filtered = items.filter(function (item) {
      var status = item.getAttribute('data-status');
      if (state.status && status !== state.status) {
        return false;
      }
      return matchesSearch(item, state.query);
    });

    filtered.sort(function (a, b) {
      var aDate = parseDate(a.getAttribute('data-date'));
      var bDate = parseDate(b.getAttribute('data-date'));
      return state.sort === 'asc' ? aDate - bDate : bDate - aDate;
    });

    list.innerHTML = '';
    items.forEach(function (item) {
      item.classList.remove('active');
    });

    filtered.forEach(function (item, index) {
      if (index === 0) {
        item.classList.add('active');
      }
      list.appendChild(item);
    });

    if (emptyState) {
      emptyState.style.display = filtered.length ? 'none' : 'block';
    }
    updateQueueBadge();
  }

  filterButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      state.status = button.getAttribute('data-status-filter');
      filterButtons.forEach(function (btn) {
        btn.classList.toggle('active', btn === button);
      });
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', function (event) {
      state.query = event.target.value.trim().toLowerCase();
      applyFilters();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', function (event) {
      state.sort = event.target.value;
      applyFilters();
    });
  }

  applyFilters();
});
