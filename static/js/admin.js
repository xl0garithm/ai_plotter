(() => {
  const tableBody = document.querySelector("#queue-table tbody");

  async function fetchQueue() {
    try {
      const response = await fetch("/api/admin/jobs");
      
      // Check if we got redirected to login page (HTML response instead of JSON)
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("text/html")) {
        window.location.reload();
        return;
      }
      
      if (!response.ok) throw new Error("Failed to fetch queue");
      const jobs = await response.json();
      renderQueue(jobs);
    } catch (err) {
      console.error(err);
    }
  }

  function renderQueue(jobs) {
    tableBody.innerHTML = "";
    if (jobs.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="5" style="text-align: center; color: var(--text-muted);">No jobs in queue</td>`;
      tableBody.appendChild(tr);
      return;
    }

    jobs.forEach((job) => {
      const tr = document.createElement("tr");
      const status = (job.status || "").toLowerCase();
      const canApprove = ["generated", "confirmed"].includes(status);
      const canStart = ["approved", "confirmed", "queued"].includes(status);
      const canReprint = status !== "printing" && status !== "queued";
      const canCancel = !["completed", "cancelled"].includes(status);

      // Add classes for button styling
      tr.innerHTML = `
        <td>${job.id}</td>
        <td><span class="status-badge">${job.status}</span></td>
        <td>${new Date(job.created_at).toLocaleString()}</td>
        <td>${job.requester || "N/A"}</td>
        <td>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button data-action="approve" data-id="${job.id}" ${!canApprove ? "disabled" : ""}>Approve</button>
            <button data-action="start" data-id="${job.id}" ${!canStart ? "disabled" : ""}>Start</button>
            <button class="secondary" data-action="reprint" data-id="${job.id}" ${!canReprint ? "disabled" : ""}>Reprint</button>
            <button class="danger" data-action="cancel" data-id="${job.id}" ${!canCancel ? "disabled" : ""}>Cancel</button>
          </div>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  }

  async function handleAction(action, jobId) {
    const endpoint = action === "reprint" ? "start?reprint=1" : action;
    
    // Visual feedback
    const btn = document.querySelector(`button[data-action="${action}"][data-id="${jobId}"]`);
    const originalText = btn ? btn.textContent : "";
    if (btn) {
        btn.disabled = true;
        btn.textContent = "...";
    }

    try {
      const response = await fetch(`/api/admin/jobs/${jobId}/${endpoint}`, {
        method: "POST",
      });
      
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("text/html")) {
        window.location.reload();
        return;
      }

      if (!response.ok) throw new Error(`${action} failed`);
      await fetchQueue();
    } catch (err) {
      console.error(err);
      alert(`${action} failed`);
      if (btn) {
          btn.disabled = false;
          btn.textContent = originalText;
      }
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

  // Poll every 4 seconds
  setInterval(fetchQueue, 4000);
  fetchQueue();

  const uploadForm = document.getElementById("manual-upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fileInput = uploadForm.querySelector('input[type="file"]');
      const submitBtn = uploadForm.querySelector('button[type="submit"]');
      
      if (!fileInput?.files?.length) {
        alert("Select an image first.");
        return;
      }

      if (submitBtn) submitBtn.disabled = true;

      const formData = new FormData();
      formData.append("image", fileInput.files[0]);
      try {
        const response = await fetch("/api/admin/uploads", {
          method: "POST",
          body: formData,
        });
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("text/html")) {
          window.location.reload();
          return;
        }

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.error || "Upload failed");
        }
        fileInput.value = "";
        await fetchQueue();
        alert("Image uploaded and queued.");
      } catch (err) {
        console.error(err);
        alert(err.message || "Upload failed");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
})();
