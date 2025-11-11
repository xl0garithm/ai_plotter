(() => {
  const video = document.getElementById("webcam");
  const canvas = document.getElementById("snapshot");
  const ctx = canvas.getContext("2d");
  const startBtn = document.getElementById("start-btn");
  const captureBtn = document.getElementById("capture-btn");
  const retakeBtn = document.getElementById("retake-btn");
  const submitBtn = document.getElementById("submit-btn");
  const previewSection = document.getElementById("preview-section");
  const generatedPreview = document.getElementById("generated-preview");
  const confirmBtn = document.getElementById("confirm-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const jobStatusList = document.getElementById("job-status");

  let stream;
  let capturedBlob;
  let currentJobId;

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      captureBtn.disabled = false;
      startBtn.disabled = true;
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Unable to access the camera.");
    }
  }

  function capturePhoto() {
    const width = video.videoWidth;
    const height = video.videoHeight;
    canvas.width = width;
    canvas.height = height;
    ctx.drawImage(video, 0, 0, width, height);
    canvas.hidden = false;
    captureBtn.disabled = true;
    retakeBtn.disabled = false;
    submitBtn.disabled = false;
    canvas.toBlob((blob) => {
      capturedBlob = blob;
    }, "image/png");
  }

  function retakePhoto() {
    capturedBlob = null;
    canvas.hidden = true;
    captureBtn.disabled = false;
    submitBtn.disabled = true;
    retakeBtn.disabled = true;
  }

  async function submitPhoto() {
    if (!capturedBlob) return;
    const formData = new FormData();
    formData.append("image", capturedBlob, "capture.png");

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Failed to submit job");
      const data = await response.json();
      currentJobId = data.job_id;
      await loadPreview(currentJobId);
    } catch (err) {
      console.error(err);
      alert("Submission failed.");
    }
  }

  async function loadPreview(jobId) {
    try {
      const response = await fetch(`/api/jobs/${jobId}/preview`);
      if (!response.ok) throw new Error("Failed to load preview");
      const blob = await response.blob();
      generatedPreview.src = URL.createObjectURL(blob);
      previewSection.hidden = false;
    } catch (err) {
      console.error(err);
      alert("Could not load preview.");
    }
  }

  async function confirmJob() {
    if (!currentJobId) return;
    try {
      const response = await fetch(`/api/jobs/${currentJobId}/confirm`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Confirmation failed");
      resetUI();
      pollJobs();
    } catch (err) {
      console.error(err);
      alert("Could not confirm job.");
    }
  }

  async function cancelJob() {
    if (!currentJobId) return;
    try {
      const response = await fetch(`/api/jobs/${currentJobId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Cancellation failed");
      resetUI();
      pollJobs();
    } catch (err) {
      console.error(err);
      alert("Could not cancel job.");
    }
  }

  function resetUI() {
    if (stream) {
      captureBtn.disabled = false;
      retakeBtn.disabled = true;
      submitBtn.disabled = true;
      previewSection.hidden = true;
      canvas.hidden = true;
    }
    currentJobId = null;
  }

  async function pollJobs() {
    try {
      const response = await fetch("/api/jobs");
      if (!response.ok) throw new Error("Failed to fetch jobs");
      const jobs = await response.json();
      renderJobs(jobs);
    } catch (err) {
      console.error("Job polling failed:", err);
    }
  }

  function renderJobs(jobs) {
    jobStatusList.innerHTML = "";
    jobs.forEach((job) => {
      const li = document.createElement("li");
      li.textContent = `#${job.id} - ${job.status}`;
      jobStatusList.appendChild(li);
    });
  }

  startBtn.addEventListener("click", startCamera);
  captureBtn.addEventListener("click", capturePhoto);
  retakeBtn.addEventListener("click", retakePhoto);
  submitBtn.addEventListener("click", submitPhoto);
  confirmBtn.addEventListener("click", confirmJob);
  cancelBtn.addEventListener("click", cancelJob);

  setInterval(pollJobs, 5000);
  pollJobs();
})();

