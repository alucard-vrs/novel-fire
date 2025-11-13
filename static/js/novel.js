(() => {
  const synopsisWrap = document.querySelector('[data-synopsis]');
  if (synopsisWrap) {
    const toggle = synopsisWrap.querySelector('[data-synopsis-toggle]');
    const content = synopsisWrap.querySelector('[data-synopsis-body]');
    if (toggle && content) {
      toggle.addEventListener('click', () => {
        const expanded = content.classList.toggle('is-expanded');
        content.classList.toggle('is-collapsed', !expanded);
        toggle.setAttribute('aria-expanded', String(expanded));
        toggle.textContent = expanded ? 'Show Less' : 'More';
      });
    }
  }

  const groupToggle = document.querySelector('[data-group-toggle]');
  const extraGrid = document.querySelector('[data-group-extra]');
  if (groupToggle && extraGrid) {
    groupToggle.addEventListener('click', () => {
      const willShow = extraGrid.hasAttribute('hidden');
      if (willShow) {
        extraGrid.removeAttribute('hidden');
      } else {
        extraGrid.setAttribute('hidden', '');
      }
      groupToggle.setAttribute('aria-expanded', String(willShow));
      groupToggle.textContent = willShow ? 'Hide groups' : 'View all groups';
    });
  }
})();
