// // src/pages/WelcomePage.tsx
// import React, { useEffect, useState } from "react";

// interface WelcomePageProps {
//   onFinish: () => void; // FIXED NAME
// }

// export default function WelcomePage({ onFinish }: WelcomePageProps) {
//   const [displayText, setDisplayText] = useState("");

//   const screenText = "Welcome...";
//   const voiceText = "Welcome to the medical Assistant Bot.";

//   useEffect(() => {
//     speechSynthesis.cancel();
//     const msg = new SpeechSynthesisUtterance(voiceText);
//     msg.lang = "en-US";
//     speechSynthesis.speak(msg);

//     let index = 0;
//     const typingInterval = setInterval(() => {
//       setDisplayText(screenText.slice(0, index));
//       index++;
//       if (index > screenText.length) clearInterval(typingInterval);
//     }, 80);

//     const switchTimer = setTimeout(() => {
//       onFinish(); // FIXED CALLBACK
//     }, 4000);

//     return () => {
//       clearInterval(typingInterval);
//       clearTimeout(switchTimer);
//       speechSynthesis.cancel();
//     };
//   }, []);

//   return (
//     <div className="welcome-fullscreen">
//       <div className="center-content">
//         <img src="/bot.png" alt="Bot" className="bot-image" />
//         <h1 className="welcome-text">{displayText}</h1>
//       </div>

//       <style>{`
//         body { margin: 0; padding: 0; overflow: hidden; }

//         .welcome-fullscreen {
//           position: relative;
//           width: 100vw;
//           height: 100vh;
//           background: white;
//           display: flex;
//           justify-content: center;
//           align-items: center;
//           overflow: hidden;
//         }

//         .bot-image {
//           width: 200px;
//           animation: bounce 1.3s infinite;
//         }
//         @keyframes bounce {
//           0%,100% { transform: translateY(0); }
//           50% { transform: translateY(-20px); }
//         }

//         .welcome-text {
//           margin-top: 20px;
//           font-size: 32px;
//           font-family: Arial, sans-serif;
//           color: #333;
//         }
//       `}</style>
//     </div>
//   );
// }




import React, { useEffect, useState } from "react";

interface WelcomePageProps {
  onFinish: () => void;
}

export default function WelcomePage({ onFinish }: WelcomePageProps) {
  const [displayText, setDisplayText] = useState("");

  const screenText = "Welcome to MediCare ";
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
      onFinish();
    }, 4500);

    return () => {
      clearInterval(typingInterval);
      clearTimeout(switchTimer);
      speechSynthesis.cancel();
    };
  }, [onFinish]);

  return (
    <div style={styles.container}>
      <div style={styles.heroOverlay}>
        <div style={styles.heroContent}>
          <div style={styles.botImageContainer}>
            <img src="/bot.png" alt="Bot" style={styles.botImage} />
          </div>
          <h1 style={styles.heroTitle}>{displayText}</h1>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }
      `}</style>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: { position: "relative", height: "100vh", overflow: "hidden" },
  heroOverlay: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    display: "flex", flexDirection: "column",
    justifyContent: "center", alignItems: "center",
    zIndex: 1,
  },
  heroContent: {
    textAlign: "center", color: "white",
    zIndex: 2, position: "relative",
    padding: "0 20px",
  },
  botImageContainer: {
    marginBottom: "2rem",
    backgroundColor: "transparent",  // no background to blend with gradient
    borderRadius: 0,                 // remove border radius for no distinct shape
    display: "inline-block",
  },
  botImage: {
    width: 200,
    height: 200,
    animation: "bounce 1.3s infinite",
    objectFit: "contain",
    backgroundColor: "transparent", // make sure image bg is transparent
    display: "block",
  },
  heroTitle: {
    fontSize: "3rem",
    marginBottom: "1rem",
    fontWeight: "bold",
    textShadow: "0 2px 4px rgba(0,0,0,0.3)",
    minHeight: "80px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
};
