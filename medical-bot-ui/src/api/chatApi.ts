// src/api/chatApi.ts
export async function sendMessageToBackend(message: string) {
  try {
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch from backend");
    }

    const data = await response.json();
    return data.reply; // FastAPI returns { reply: "..." }
  } catch (err) {
    console.error(err);
    return "Error communicating with server.";
  }
}
