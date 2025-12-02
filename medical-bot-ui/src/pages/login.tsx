// import React, { useState } from "react";

// interface HomePageProps {
//   onLoginSuccess: () => void;
//   onNavigateToSignUp: () => void; // add this prop to trigger signup navigation externally
// }

// export default function HomePage({ onLoginSuccess, onNavigateToSignUp }: HomePageProps) {
//   const [isPopupOpen, setIsPopupOpen] = useState(true);
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error, setError] = useState("");

//   const handleLogin = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!username || !password) {
//       setError("Please enter username and password.");
//       return;
//     }

//     const storedUsername = localStorage.getItem("username");
//     const storedPassword = localStorage.getItem("password");

//     if (username === storedUsername && password === storedPassword) {
//       setError("");
//       setIsPopupOpen(false);
//       onLoginSuccess(); // parent component decides what to do on login success
//     } else {
//       setError("Invalid username or password.");
//     }
//   };

//   const handleSignUp = () => {
//     setIsPopupOpen(false);
//     onNavigateToSignUp(); // parent handles navigation to SignUp page or component
//   };

//   const handleClosePopup = () => {
//     setIsPopupOpen(false);
//   };

//   return (
//     <div style={styles.container}>
//       {/* Medical Hero Background */}
//       <div style={styles.heroOverlay}>
//         <div style={styles.heroContent}>
//           <h1 style={styles.heroTitle}>MediCare Portal</h1>
//           <p style={styles.heroSubtitle}>Welcome to your medical dashboard</p>
//         </div>
//       </div>

//       {/* Login Popup */}
//       {isPopupOpen && (
//         <div style={styles.popupOverlay}>
//           <div style={styles.popupContent}>
//             <div style={styles.closeButton} onClick={handleClosePopup}>×</div>
//             <form onSubmit={handleLogin} style={styles.form}>
//               <h2 style={styles.title}>Access Your Account</h2>
//               {error && <div style={styles.error}>{error}</div>}
//               <input
//                 type="text"
//                 placeholder="Username"
//                 value={username}
//                 onChange={(e) => setUsername(e.target.value)}
//                 style={styles.input}
//               />
//               <input
//                 type="password"
//                 placeholder="Password"
//                 value={password}
//                 onChange={(e) => setPassword(e.target.value)}
//                 style={styles.input}
//               />
//               <div style={styles.buttonGroup}>
//                 <button type="submit" style={styles.loginButton}>Log In</button>
//                 <button type="button" onClick={handleSignUp} style={styles.signupButton}>Sign Up</button>
//               </div>
//             </form>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// const styles: { [key: string]: React.CSSProperties } = {
//   container: { position: "relative", height: "100vh", overflow: "hidden" },
//   heroOverlay: {
//     position: "absolute",
//     top: 0, left: 0, right: 0, bottom: 0,
//     background: "#fff",
//     //"linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
//     display: "flex",
//     flexDirection: "column",
//     justifyContent: "center",
//     alignItems: "center",
//     zIndex: 1,
//   },
//   heroContent: { textAlign: "center", color: "white", zIndex: 2, position: "relative" },
//   heroTitle: {
//     fontSize: "3rem", marginBottom: "1rem", fontWeight: "bold",
//     textShadow: "0 2px 4px rgba(0,0,0,0.3)",
//   },
//   heroSubtitle: {
//     fontSize: "1.2rem", opacity: 0.9, textShadow: "0 1px 2px rgba(0,0,0,0.3)",
//   },
//   popupOverlay: {
//     position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
//     backgroundColor: "rgba(0,0,0,0.6)",
//     display: "flex", justifyContent: "center", alignItems: "center",
//     zIndex: 1000,
//   },
//   popupContent: {
//     backgroundColor: "#fff", padding: 40, borderRadius: 12,
//     boxShadow: "0 20px 40px rgba(0,0,0,0.3)", width: 380, maxWidth: "90vw",
//     position: "relative",
//   },
//   closeButton: {
//     position: "absolute", top: 15, right: 20,
//     background: "none", border: "none", fontSize: "24px", cursor: "pointer",
//     color: "#999", width: 30, height: 30,
//     display: "flex", alignItems: "center", justifyContent: "center",
//   },
//   form: { display: "flex", flexDirection: "column" },
//   title: { marginBottom: 20, textAlign: "center", color: "#333" },
//   input: {
//     height: 40, marginBottom: 15, borderRadius: 4, border: "1px solid #ccc",
//     paddingLeft: 10, fontSize: 16,
//   },
//   buttonGroup: { display: "flex", gap: 10, marginTop: 5 },
//   loginButton: {
//     flex: 1, height: 42, backgroundColor: "#2563eb", color: "#fff",
//     border: "none", borderRadius: 4, fontSize: 16, cursor: "pointer",
//   },
//   signupButton: {
//     flex: 1, height: 42, backgroundColor: "#10b981", color: "#fff",
//     border: "none", borderRadius: 4, fontSize: 16, cursor: "pointer",
//   },
//   error: { marginBottom: 15, color: "red", fontSize: 14, textAlign: "center" },
// };

import React, { useState } from "react";

interface HomePageProps {
  onLoginSuccess: () => void;
  onNavigateToSignUp: () => void;
}

export default function HomePage({ onLoginSuccess, onNavigateToSignUp }: HomePageProps) {
  const [isPopupOpen, setIsPopupOpen] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please enter username and password.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json" 
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Invalid username or password.");
        return;
      }

      // ✅ Login successful - store user info for chat history
      localStorage.setItem("user_email", data.email || `${username}@example.com`);
      localStorage.setItem("username", username);
      
      setIsPopupOpen(false);
      onLoginSuccess(); // Navigate to MedicalBot
      
    } catch (error) {
      console.error("Login error:", error);
      setError("Server error. Make sure backend is running on port 8000.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = () => {
    setIsPopupOpen(false);
    onNavigateToSignUp();
  };

  const handleClosePopup = () => {
    setIsPopupOpen(false);
  };

  return (
    <div style={styles.container}>
      {/* Medical Hero Background */}
      <div style={styles.heroOverlay}>
        <div style={styles.heroContent}>
          <h1 style={styles.heroTitle}>MediCare Portal</h1>
          <p style={styles.heroSubtitle}>Welcome to your medical dashboard</p>
        </div>
      </div>

      {/* Login Popup */}
      {isPopupOpen && (
        <div style={styles.popupOverlay}>
          <div style={styles.popupContent}>
            <div style={styles.closeButton} onClick={handleClosePopup}>×</div>
            <form onSubmit={handleLogin} style={styles.form}>
              <h2 style={styles.title}>Access Your Account</h2>
              {error && <div style={styles.error}>{error}</div>}
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={styles.input}
                disabled={isLoading}
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={styles.input}
                disabled={isLoading}
              />
              <div style={styles.buttonGroup}>
                <button 
                  type="submit" 
                  style={{
                    ...styles.loginButton,
                    opacity: isLoading ? 0.7 : 1,
                    cursor: isLoading ? "not-allowed" : "pointer"
                  }} 
                  disabled={isLoading}
                >
                  {isLoading ? "Logging in..." : "Log In"}
                </button>
                <button 
                  type="button" 
                  onClick={handleSignUp} 
                  style={styles.signupButton}
                  disabled={isLoading}
                >
                  Sign Up
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: { position: "relative", height: "100vh", overflow: "hidden" },
  heroOverlay: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: "#fff",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1,
  },
  heroContent: { textAlign: "center", color: "white", zIndex: 2, position: "relative" },
  heroTitle: {
    fontSize: "3rem", marginBottom: "1rem", fontWeight: "bold",
    textShadow: "0 2px 4px rgba(0,0,0,0.3)",
  },
  heroSubtitle: {
    fontSize: "1.2rem", opacity: 0.9, textShadow: "0 1px 2px rgba(0,0,0,0.3)",
  },
  popupOverlay: {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.6)",
    display: "flex", justifyContent: "center", alignItems: "center",
    zIndex: 1000,
  },
  popupContent: {
    backgroundColor: "#fff", padding: 40, borderRadius: 12,
    boxShadow: "0 20px 40px rgba(0,0,0,0.3)", width: 380, maxWidth: "90vw",
    position: "relative",
  },
  closeButton: {
    position: "absolute", top: 15, right: 20,
    background: "none", border: "none", fontSize: "24px", cursor: "pointer",
    color: "#999", width: 30, height: 30,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  form: { display: "flex", flexDirection: "column" },
  title: { marginBottom: 20, textAlign: "center", color: "#333" },
  input: {
    height: 40, marginBottom: 15, borderRadius: 4, border: "1px solid #ccc",
    paddingLeft: 10, fontSize: 16,
  },
  buttonGroup: { display: "flex", gap: 10, marginTop: 5 },
  loginButton: {
    flex: 1, height: 42, backgroundColor: "#2563eb", color: "#fff",
    border: "none", borderRadius: 4, fontSize: 16, cursor: "pointer",
  },
  signupButton: {
    flex: 1, height: 42, backgroundColor: "#10b981", color: "#fff",
    border: "none", borderRadius: 4, fontSize: 16, cursor: "pointer",
  },
  error: { marginBottom: 15, color: "red", fontSize: 14, textAlign: "center" },
};
