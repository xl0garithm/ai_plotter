(() => {
  const tableBody = document.querySelector("#queue-table tbody");
  const overlayEl = document.getElementById("print-progress-overlay");
  const overlayJobEl = document.getElementById("print-progress-job-id");
  const overlayBarEl = document.getElementById("print-progress-bar");
  const overlayPercentEl = document.getElementById("print-progress-percent");
  const overlayEtaEl = document.getElementById("print-progress-eta");
  let overlayTimer = null;
  let overlayJobData = null;

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
      tr.innerHTML = `<td colspan="6" style="text-align: center; color: var(--text-muted);">No jobs in queue</td>`;
      tableBody.appendChild(tr);
      setOverlayJob(null);
      return;
    }

    let activePrintJob = null;

    jobs.forEach((job) => {
      const tr = document.createElement("tr");
      const status = (job.status || "").toLowerCase();
      const canApprove = ["generated", "confirmed"].includes(status);
      const canStart = ["approved", "confirmed", "queued"].includes(status);
      const canReprint = status !== "printing" && status !== "queued";
      const canCancel = !["completed", "cancelled"].includes(status);

      if (!activePrintJob && status === "printing") {
        activePrintJob = job;
      }

      tr.innerHTML = `
        <td>${job.id}</td>
        <td><span class="status-badge">${job.status}</span></td>
        <td>${new Date(job.created_at).toLocaleString()}</td>
        <td>${job.email || "—"}</td>
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

    setOverlayJob(activePrintJob);
    if (activePrintJob) {
      tableBody.querySelectorAll('button[data-action="start"]').forEach((btn) => {
        btn.disabled = true;
      });
    }
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

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds)) return "—";
    const totalSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0 || hours > 0) parts.push(`${minutes.toString().padStart(2, "0")}m`);
    parts.push(`${secs.toString().padStart(2, "0")}s`);
    return parts.join(" ");
  }

  function updateOverlayDisplay() {
    if (!overlayJobData || !overlayEl || overlayEl.hasAttribute("hidden")) {
      return;
    }
    const now = Date.now();
    const estimate = Number.isFinite(overlayJobData.estimatedSeconds)
      ? overlayJobData.estimatedSeconds
      : null;
    const startedAt = overlayJobData.startedAt;
    let progress = 0;
    let remaining = estimate;

    if (estimate && startedAt) {
      const elapsed = Math.max((now - startedAt) / 1000, 0);
      progress = Math.min(elapsed / estimate, 1);
      remaining = Math.max(estimate - elapsed, 0);
    } else if (startedAt) {
      const elapsed = Math.max((now - startedAt) / 1000, 0);
      remaining = null;
      progress = Math.min(elapsed / 600, 0.95); // fallback: assume 10 min job
    }

    if (overlayBarEl) {
      overlayBarEl.style.width = `${(progress * 100).toFixed(1)}%`;
    }
    if (overlayPercentEl) {
      overlayPercentEl.textContent = `${Math.round(progress * 100)}%`;
    }
    if (overlayEtaEl) {
      overlayEtaEl.textContent = remaining != null ? `${formatDuration(remaining)} remaining` : "Estimating…";
    }
  }

  function setOverlayJob(job) {
    if (!overlayEl) return;

    if (!job) {
      overlayJobData = null;
      overlayEl.setAttribute("hidden", "true");
      if (overlayBarEl) overlayBarEl.style.width = "0%";
      if (overlayPercentEl) overlayPercentEl.textContent = "0%";
      if (overlayEtaEl) overlayEtaEl.textContent = "Idle";
      if (overlayTimer) {
        clearInterval(overlayTimer);
        overlayTimer = null;
      }
      return;
    }

    const estimatedSeconds = Number.parseFloat(job?.metadata?.estimated_print_seconds);
    overlayJobData = {
      id: job.id,
      startedAt: job.started_at ? Date.parse(job.started_at) : null,
      estimatedSeconds: Number.isFinite(estimatedSeconds) ? estimatedSeconds : null,
    };

    overlayEl.removeAttribute("hidden");
    if (overlayJobEl) {
      overlayJobEl.textContent = job.id;
    }
    updateOverlayDisplay();
    if (!overlayTimer) {
      overlayTimer = setInterval(updateOverlayDisplay, 500);
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
