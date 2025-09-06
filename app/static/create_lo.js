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
  p.innerHTML = "Saving…";

  try {
    // 1. Find the save form
    const saveForm = document.querySelector('form[action*="lo_save"]');
    if (saveForm) {
      const fd = new FormData(saveForm);
      // Post to the lo_save route
      await fetch(saveForm.action, {
        method: "POST",
        body: fd
      });
    }

    // 2. Now run the evaluation (your original code)
    p.innerHTML = "Evaluating…";
    const res = await fetch(`${AI_EVALUATE_URL}?unit_id=${encodeURIComponent(UNIT_ID)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: UNIT_ID })
    });
    const data = await res.json();

    if (!data.ok) throw new Error(data.error || `HTTP ${res.status}`);

    p.innerHTML = data.html;
  } catch (err) {
    p.innerHTML = `<div class="text-danger">❌ AI evaluation failed: ${String(err)}`;
  }
});

})();
});
