// src/App.tsx
import React, { useState, useEffect } from "react";
import WelcomePage from "./pages/WelcomePage";
import Login from "./pages/login";
import SignUp from "./pages/SignUp";
import MedicalBotUI from "./pages/MedicalBotUI";
export default function App() {
  const [currentPage, setCurrentPage] = useState<"welcome"| "signup" | "login" | "chat">("welcome");

  useEffect(() => {
    const savedUser = localStorage.getItem("username");
    const savedPass = localStorage.getItem("password");
    if (savedUser && savedPass) {
      setCurrentPage("welcome"); // or "login" depending on flow
    } else {
      setCurrentPage("signup"); // show sign up if no credentials saved
    }
  }, []);
  const handleWelcomeFinish = () => {
    setCurrentPage("login");
  };

  
  const handleNavigateToSignUp = () => {
    setCurrentPage("signup"); // Handle HomePage SignUp navigation
  };

  const handleSignUpSuccess = (username: string , email: string, password: string) => {
    // Save user credentials (insecure, just example)
    localStorage.setItem("username", username);
    localStorage.setItem("email", email);
    localStorage.setItem("password", password);
    setCurrentPage("login");
  };
  const handleLoginSuccess = () => {
    setCurrentPage("chat");
  };

  return (
    <>
      {currentPage === "welcome" && <WelcomePage onFinish={handleWelcomeFinish} />}
      {currentPage === "signup" && <SignUp onSignUpSuccess={handleSignUpSuccess} />}
      {currentPage === "login" &&<Login 
          onLoginSuccess={handleLoginSuccess}
          onNavigateToSignUp={handleNavigateToSignUp} // Pass this callback
        />}
      {currentPage === "chat" && <MedicalBotUI />}
    </>
  );
}
// export default function App() {
//   const [showBotUI, setShowBotUI] = useState(false);

//   return (
//     <>
//       {showBotUI ? (
//         <MedicalBotUI />
//       ) : (
//         <WelcomePage onFinish={() => setShowBotUI(true)} />
//       )}
//     </>
//   );
// }
