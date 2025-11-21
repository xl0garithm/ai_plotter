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
  const captureSection = document.getElementById("capture-section");
  const layoutGrid = document.querySelector(".layout-grid");
  const emailInput = document.getElementById("email-input");
  const captureMediaContainer = document.querySelector("#capture-section .media-container");
  const styleDescription = document.getElementById("style-description");
  const styleRadios = document.querySelectorAll('input[name="style"]');
  const alignmentOverlay = document.getElementById("alignment-overlay");

  const STYLE_PRESETS = window.STYLE_PRESETS || {};
  const DEFAULT_STYLE_KEY = Object.keys(STYLE_PRESETS)[0] || "nerdy";

  function updateStyleDescription(styleKey) {
    const fallback = Object.values(STYLE_PRESETS)[0] || null;
    const preset = STYLE_PRESETS[styleKey] || fallback;
    if (styleDescription) {
      styleDescription.textContent = preset?.description || "";
    }
  }

  styleRadios.forEach((radio) => {
    radio.addEventListener("change", () => updateStyleDescription(radio.value));
  });
  updateStyleDescription(document.querySelector('input[name="style"]:checked')?.value || DEFAULT_STYLE_KEY);

  let stream;
  let capturedBlob;
  let currentJobId;

  function setAlignmentOverlayVisibility(shouldShow) {
    if (!alignmentOverlay) return;
    alignmentOverlay.hidden = !shouldShow;
  }

  function updateCaptureAspectRatio() {
    if (!captureMediaContainer || !video.videoWidth || !video.videoHeight) return;
    captureMediaContainer.style.aspectRatio = `${video.videoWidth} / ${video.videoHeight}`;
    captureMediaContainer.style.setProperty("--media-aspect", `${video.videoWidth} / ${video.videoHeight}`);
  }

  video?.addEventListener("loadedmetadata", updateCaptureAspectRatio);

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      video.hidden = false;
      canvas.hidden = true;
      captureBtn.disabled = false;
      startBtn.hidden = true; // Hide start button once started
      setAlignmentOverlayVisibility(true);
      // Metadata may already be available once the stream starts playing
      if (video.readyState >= 2) {
        updateCaptureAspectRatio();
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Unable to access the camera. Please ensure you have granted permission.");
      setAlignmentOverlayVisibility(false);
    }
  }

  function capturePhoto() {
    if (!video.srcObject) return;
    
    const width = video.videoWidth;
    const height = video.videoHeight;
    canvas.width = width;
    canvas.height = height;
    ctx.drawImage(video, 0, 0, width, height);
    updateCaptureAspectRatio();
    
    video.hidden = true;
    canvas.hidden = false;
    setAlignmentOverlayVisibility(false);
    
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
    setAlignmentOverlayVisibility(true);
    
    captureBtn.disabled = false;
    submitBtn.disabled = true;
    retakeBtn.disabled = true;
  }

  async function submitPhoto() {
    if (!capturedBlob) return;

    const emailValue = emailInput?.value.trim();
    submitBtn.disabled = true;
    submitBtn.textContent = "Generating...";

    const formData = new FormData();
    formData.append("image", capturedBlob, "capture.png");
    if (emailValue) {
      formData.append("email", emailValue);
    }

    // Get selected style
    const selectedStyle = document.querySelector('input[name="style"]:checked')?.value || DEFAULT_STYLE_KEY;
    formData.append("style", selectedStyle);

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
            layoutGrid?.classList.add("has-preview");
            captureBtn.disabled = true;
            retakeBtn.disabled = true;
            submitBtn.disabled = true;
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
    layoutGrid?.classList.remove("has-preview");
    
    // Reset camera controls
    video.hidden = false;
    canvas.hidden = true;
    setAlignmentOverlayVisibility(Boolean(stream));
    
    captureBtn.disabled = false;
    retakeBtn.disabled = true;
    submitBtn.disabled = true;
    submitBtn.textContent = "Generate";
    if (emailInput) {
      emailInput.value = "";
    }
    
    if (!stream) {
        startCamera();
    }
  }

  startBtn.addEventListener("click", startCamera);
  captureBtn.addEventListener("click", capturePhoto);
  retakeBtn.addEventListener("click", retakePhoto);
  submitBtn.addEventListener("click", submitPhoto);
  confirmBtn.addEventListener("click", confirmJob);
  cancelBtn.addEventListener("click", cancelJob);

})();
