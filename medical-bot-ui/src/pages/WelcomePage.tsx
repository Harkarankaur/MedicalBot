// src/pages/WelcomePage.tsx
import React, { useEffect, useState } from "react";

interface WelcomePageProps {
  onFinish: () => void; // FIXED NAME
}

export default function WelcomePage({ onFinish }: WelcomePageProps) {
  const [displayText, setDisplayText] = useState("");

  const screenText = "Welcome...";
  const voiceText = "Welcome to the medical Assistant Bot.";

  useEffect(() => {
    speechSynthesis.cancel();
    const msg = new SpeechSynthesisUtterance(voiceText);
    msg.lang = "en-US";
    speechSynthesis.speak(msg);

    let index = 0;
    const typingInterval = setInterval(() => {
      setDisplayText(screenText.slice(0, index));
      index++;
      if (index > screenText.length) clearInterval(typingInterval);
    }, 80);

    const switchTimer = setTimeout(() => {
      onFinish(); // FIXED CALLBACK
    }, 4000);

    return () => {
      clearInterval(typingInterval);
      clearTimeout(switchTimer);
      speechSynthesis.cancel();
    };
  }, []);

  return (
    <div className="welcome-fullscreen">
      <div className="center-content">
        <img src="/bot.png" alt="Bot" className="bot-image" />
        <h1 className="welcome-text">{displayText}</h1>
      </div>

      <style>{`
        body { margin: 0; padding: 0; overflow: hidden; }

        .welcome-fullscreen {
          position: relative;
          width: 100vw;
          height: 100vh;
          background: white;
          display: flex;
          justify-content: center;
          align-items: center;
          overflow: hidden;
        }

        .bot-image {
          width: 200px;
          animation: bounce 1.3s infinite;
        }
        @keyframes bounce {
          0%,100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }

        .welcome-text {
          margin-top: 20px;
          font-size: 32px;
          font-family: Arial, sans-serif;
          color: #333;
        }
      `}</style>
    </div>
  );
}
