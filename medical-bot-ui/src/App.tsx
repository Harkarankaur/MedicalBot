// src/App.tsx
import React, { useState, useEffect } from "react";
import WelcomePage from "./pages/WelcomePage";
//import Login from "./pages/login";
import MedicalBotUI from "./pages/MedicalBotUI";
// export default function App() {
//   const [currentPage, setCurrentPage] = useState<"welcome" | "login" | "chat">("welcome");

//   const handleWelcomeFinish = () => {
//     setCurrentPage("login");
//   };

//   const handleLoginSuccess = () => {
//     setCurrentPage("chat");
//   };

//   return (
//     <>
//       {currentPage === "welcome" && <WelcomePage onFinish={handleWelcomeFinish} />}
//       {currentPage === "login" && <Login onLoginSuccess={handleLoginSuccess} />}
//       {currentPage === "chat" && <MedicalBotUI />}
//     </>
//   );
// }
export default function App() {
  const [showBotUI, setShowBotUI] = useState(false);

  return (
    <>
      {showBotUI ? (
        <MedicalBotUI />
      ) : (
        <WelcomePage onFinish={() => setShowBotUI(true)} />
      )}
    </>
  );
}
