(function () {
  const D = window.HEALTHSYNC_DATA;
  let phase = "awaiting";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pill = (tone, text) => `<span class="pill pill--${tone}">${esc(text)}</span>`;

  function render() {
    const p = D.phases[phase];

    $("header-pill").innerHTML = pill(p.header.tone, p.header.text);

    $("stages").innerHTML = p.stages
      .map((s) => `<div><div class="stage-label">${esc(s.label)}</div>${pill(s.tone, s.text)}</div>`)
      .join("");

    $("pa-steps").innerHTML = p.paSteps
      .map(([label, state]) => `<li class="${state}"><span class="dot dot--${state}" aria-hidden="true"></span>${esc(label)}</li>`)
      .join("");

    $("stock-fill").style.width = p.stock + "%";

    $("supply-list").innerHTML = p.supply
      .map((r) => `<div><span>${esc(r.label)}</span>${pill(r.tone, r.text)}</div>`)
      .join("");

    $("trace").innerHTML = D.baseTrace.concat(p.extraTrace)
      .map((t) => `<div><b>${esc(t.who)}</b> · ${esc(t.action)}${t.detail ? `<div class="detail">${esc(t.detail)}</div>` : ""}</div>`)
      .join("");

    const approve = $("approve");
    approve.textContent = p.approveLabel;
    approve.disabled = !p.canApprove;
  }

  $("approve").addEventListener("click", () => { phase = "submitted"; render(); });
  $("reset").addEventListener("click", () => { phase = "awaiting"; render(); });
  $("review").addEventListener("click", () => {
    const card = $("sim-card");
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.focus({ preventScroll: true });
  });

  const titles = { auth: "Authorization", supply: "Supply Chain", audit: "Audit Trail" };
  document.querySelectorAll(".nav").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      document.querySelectorAll(".nav").forEach((b) => b.removeAttribute("aria-current"));
      btn.setAttribute("aria-current", "page");
      const isSafety = view === "safety";
      $("view-safety").hidden = !isSafety;
      $("view-placeholder").hidden = isSafety;
      if (!isSafety) $("placeholder-title").textContent = titles[view];
    });
  });

  render();
})();
