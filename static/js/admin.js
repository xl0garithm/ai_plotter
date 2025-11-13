(() => {
  const tableBody = document.querySelector("#queue-table tbody");

  async function fetchQueue() {
    try {
      const response = await fetch("/api/admin/jobs");
      if (!response.ok) throw new Error("Failed to fetch queue");
      const jobs = await response.json();
      renderQueue(jobs);
    } catch (err) {
      console.error(err);
    }
  }

  function renderQueue(jobs) {
    tableBody.innerHTML = "";
    jobs.forEach((job) => {
      const tr = document.createElement("tr");
      const status = (job.status || "").toLowerCase();
      const canApprove = ["generated", "confirmed"].includes(status);
      const canStart = ["approved", "confirmed", "queued"].includes(status);
      const canReprint = status !== "printing" && status !== "queued";
      const canCancel = !["completed", "cancelled"].includes(status);

      tr.innerHTML = `
        <td>${job.id}</td>
        <td>${job.status}</td>
        <td>${job.created_at}</td>
        <td>${job.requester || "N/A"}</td>
        <td>
          <button data-action="approve" data-id="${job.id}" ${!canApprove ? "disabled" : ""}>Approve</button>
          <button data-action="start" data-id="${job.id}" ${!canStart ? "disabled" : ""}>Start</button>
          <button data-action="reprint" data-id="${job.id}" ${!canReprint ? "disabled" : ""}>Reprint</button>
          <button data-action="cancel" data-id="${job.id}" ${!canCancel ? "disabled" : ""}>Cancel</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  }

  async function handleAction(action, jobId) {
    const endpoint = action === "reprint" ? "start?reprint=1" : action;
    try {
      const response = await fetch(`/api/admin/jobs/${jobId}/${endpoint}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`${action} failed`);
      await fetchQueue();
    } catch (err) {
      console.error(err);
      alert(`${action} failed`);
    }
  }

  tableBody.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;
    const action = target.dataset.action;
    const jobId = target.dataset.id;
    if (!action || !jobId) return;
    await handleAction(action, jobId);
  });

  setInterval(fetchQueue, 4000);
  fetchQueue();
})();

