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
  const captureSection = document.getElementById("capture-section");

  let stream;
  let capturedBlob;
  let currentJobId;

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      video.hidden = false;
      canvas.hidden = true;
      captureBtn.disabled = false;
      startBtn.hidden = true; // Hide start button once started
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Unable to access the camera. Please ensure you have granted permission.");
    }
  }

  function capturePhoto() {
    if (!video.srcObject) return;
    
    const width = video.videoWidth;
    const height = video.videoHeight;
    canvas.width = width;
    canvas.height = height;
    ctx.drawImage(video, 0, 0, width, height);
    
    video.hidden = true;
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
    video.hidden = false;
    canvas.hidden = true;
    
    captureBtn.disabled = false;
    submitBtn.disabled = true;
    retakeBtn.disabled = true;
  }

  async function submitPhoto() {
    if (!capturedBlob) return;
    
    submitBtn.disabled = true;
    submitBtn.textContent = "Generating...";
    
    const formData = new FormData();
    formData.append("image", capturedBlob, "capture.png");
    
    // Get selected style
    const selectedStyle = document.querySelector('input[name="style"]:checked')?.value || "normal";
    formData.append("prompt", `Make it look ${selectedStyle}.`);

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
      alert("Submission failed. Please try again.");
      submitBtn.disabled = false;
      submitBtn.textContent = "Generate";
    }
  }

  async function loadPreview(jobId) {
    try {
      // Poll for status until generated
      let attempts = 0;
      const maxAttempts = 30; // 30 * 2s = 60s timeout
      
      const checkStatus = async () => {
        if (attempts >= maxAttempts) throw new Error("Generation timed out");
        
        const response = await fetch(`/api/jobs/${jobId}`);
        if (!response.ok) throw new Error("Failed to check status");
        const job = await response.json();
        
        if (job.status === "generated") {
            // Load image
            const imgResponse = await fetch(`/api/jobs/${jobId}/preview`);
            if (!imgResponse.ok) throw new Error("Failed to load preview");
            const blob = await imgResponse.blob();
            generatedPreview.src = URL.createObjectURL(blob);
            
            previewSection.hidden = false;
            captureSection.hidden = true; // Hide capture section while previewing
            submitBtn.textContent = "Generate";
            return;
        } else if (job.status === "failed") {
            throw new Error("Generation failed: " + (job.error_message || "Unknown error"));
        }
        
        attempts++;
        setTimeout(checkStatus, 2000);
      };
      
      checkStatus();
      
    } catch (err) {
      console.error(err);
      alert("Could not load preview: " + err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Generate";
    }
  }

  async function confirmJob() {
    if (!currentJobId) return;
    confirmBtn.disabled = true;
    try {
      const response = await fetch(`/api/jobs/${currentJobId}/confirm`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Confirmation failed");
      resetUI();
      pollJobs();
      alert("Job submitted to queue successfully!");
    } catch (err) {
      console.error(err);
      alert("Could not confirm job.");
    } finally {
      confirmBtn.disabled = false;
    }
  }

  async function cancelJob() {
    if (!currentJobId) return;
    if (!confirm("Are you sure you want to discard this image?")) return;
    
    try {
      await fetch(`/api/jobs/${currentJobId}`, {
        method: "DELETE",
      });
      resetUI();
      pollJobs();
    } catch (err) {
      console.error(err);
      alert("Could not cancel job.");
    }
  }

  function resetUI() {
    currentJobId = null;
    capturedBlob = null;
    
    // Reset view to camera
    previewSection.hidden = true;
    captureSection.hidden = false;
    
    // Reset camera controls
    video.hidden = false;
    canvas.hidden = true;
    
    captureBtn.disabled = false;
    retakeBtn.disabled = true;
    submitBtn.disabled = true;
    submitBtn.textContent = "Generate";
    
    if (!stream) {
        startCamera();
    }
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
      if (['completed', 'cancelled', 'failed'].includes(job.status)) return; // Optional: filter out finished jobs
      
      const li = document.createElement("li");
      const statusClass = job.status === 'printing' ? 'text-primary' : 'text-muted';
      
      li.innerHTML = `
        <span>Job #${job.id}</span>
        <span class="status-badge">${job.status}</span>
      `;
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
