export async function analyzeImage(file, { fortName, location }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("fort_name", fortName);
  formData.append("location", location);

  const response = await fetch("/api/detect", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Analysis failed. Please try again.");
  }

  return response.json();
}

export async function askQuestion(question) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "I couldn't answer from the historical sources.");
  }

  return response.json();
}
