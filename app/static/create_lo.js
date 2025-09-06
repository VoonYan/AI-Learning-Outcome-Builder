document.addEventListener("DOMContentLoaded", function () {
  (function() {
  const tbody = document.getElementById('lo-tbody');
  if (!tbody) return;

  const sortable = new Sortable(tbody, {
    animation: 150,
    handle: '.drag-handle',
    ghostClass: 'table-active',
    onEnd: function() {
      const ids = Array.from(tbody.querySelectorAll('tr')).map(tr => tr.dataset.id);
      fetch(LO_REORDER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order: ids, unit_id: UNIT_ID })
      }).then(r => r.json()).then(data => {
        if (!data.ok) {
          console.error('Reorder failed:', data.error);
          return;
        }
        Array.from(tbody.querySelectorAll('tr')).forEach((tr, idx) => {
          const firstCell = tr.querySelector('td');
          if (firstCell) firstCell.textContent = (idx + 1).toString();
        });
      }).catch(err => console.error(err));
    }
  });

  document.getElementById("evaluateBtn")?.addEventListener("click", async () => {
  const p = document.getElementById("evaluationPanel");
  p.innerHTML = "Evaluating…";
  try {
    const res = await fetch(`${AI_EVALUATE_URL}?unit_id=${encodeURIComponent(UNIT_ID)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: UNIT_ID }) // okay even if route reads query
    });
    const data = await res.json();

    if (!data.ok) throw new Error(data.error || `HTTP ${res.status}`);

    // ⬇️ key line: render the HTML, not the whole JSON
    p.innerHTML = data.html;
  } catch (err) {
    p.innerHTML = `<div class="text-danger">AI evaluation failed: ${String(err)}</div>`;
  }
});

})();
});
