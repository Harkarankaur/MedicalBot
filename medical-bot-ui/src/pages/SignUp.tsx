// import React, { useState } from "react";

// interface SignUpProps {
//   onSignUpSuccess: (username: string, password: string) => void;
// }

// export default function SignUp({ onSignUpSuccess }: SignUpProps) {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [confirmPass, setConfirmPass] = useState("");
//   const [error, setError] = useState("");

//   const handleSubmit = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!username || !password) {
//       setError("Please enter username and password.");
//       return;
//     }
//     if (password !== confirmPass) {
//       setError("Passwords do not match.");
//       return;
//     }
//     setError("");
//     onSignUpSuccess(username, password);
//   };

//   return (
//     <div style={styles.container}>
//       <form onSubmit={handleSubmit} style={styles.form}>
//         <h2 style={styles.title}>Sign Up</h2>
//         {error && <div style={styles.error}>{error}</div>}
//         <input
//           type="text"
//           placeholder="Username"
//           value={username}
//           onChange={(e) => setUsername(e.target.value)}
//           style={styles.input}
//         />
//         <input
//           type="password"
//           placeholder="Password"
//           value={password}
//           onChange={(e) => setPassword(e.target.value)}
//           style={styles.input}
//         />
//         <input
//           type="password"
//           placeholder="Confirm Password"
//           value={confirmPass}
//           onChange={(e) => setConfirmPass(e.target.value)}
//           style={styles.input}
//         />
//         <button type="submit" style={styles.button}>
//           Sign Up
//         </button>
//       </form>
//     </div>
//   );
// }

// const styles: { [key: string]: React.CSSProperties } = {
//   container: {
//     display: "flex",
//     justifyContent: "center",
//     alignItems: "center",
//     height: "100vh",
//     backgroundColor: "#f0f2f5",
//   },
//   form: {
//     backgroundColor: "#fff",
//     padding: 30,
//     borderRadius: 8,
//     boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
//     width: 320,
//     display: "flex",
//     flexDirection: "column",
//   },
//   title: {
//     marginBottom: 20,
//     textAlign: "center",
//     color: "#333",
//   },
//   input: {
//     height: 40,
//     marginBottom: 15,
//     borderRadius: 4,
//     border: "1px solid #ccc",
//     paddingLeft: 10,
//     fontSize: 16,
//   },
//   button: {
//     height: 42,
//     backgroundColor: "#2563eb",
//     color: "#fff",
//     border: "none",
//     borderRadius: 4,
//     fontSize: 16,
//     cursor: "pointer",
//   },
//   error: {
//     marginBottom: 15,
//     color: "red",
//     fontSize: 14,
//     textAlign: "center",
//   },
// };



import React, { useState } from "react";

interface SignUpProps {
  onSignUpSuccess: (username: string,  email: string, password: string) => void;
}

export default function SignUp({ onSignUpSuccess }: SignUpProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(""); 
  const [password, setPassword] = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username  || !email || !password) {
      setError("Please enter username , email and password.");
      return;
    }
    if (password !== confirmPass) {
      setError("Passwords do not match.");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setError("");
    onSignUpSuccess(username, email, password);
  };

  const handleBackToLogin = () => {
    window.location.href = "/"; // Back to HomePage
  };

  return (
    <div style={styles.container}>
      {/* Medical Hero Background - matching HomePage */}
      <div style={styles.heroOverlay}>
        <div style={styles.heroContent}>
          <h1 style={styles.heroTitle}>MediCare Portal</h1>
          <p style={styles.heroSubtitle}>Create your medical account</p>
        </div>
      </div>

      {/* SignUp Form as Popup - matching HomePage popup style */}
      <div style={styles.popupOverlay}>
        <div style={styles.popupContent}>
          <div style={styles.closeButton} onClick={handleBackToLogin}>×</div>
          <form onSubmit={handleSubmit} style={styles.form}>
            <h2 style={styles.title}>Create Account</h2>
            {error && <div style={styles.error}>{error}</div>}
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
            />
            <input
              type="email"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
            />
            <input
              type="password"
              placeholder="Confirm Password"
              value={confirmPass}
              onChange={(e) => setConfirmPass(e.target.value)}
              style={styles.input}
            />
            <div style={styles.buttonGroup}>
              <button type="submit" style={styles.signupButton}>Sign Up</button>
              <button 
                type="button" 
                onClick={handleBackToLogin} 
                style={styles.loginButton}
              >
                Back to Home
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: { 
    position: "relative", 
    height: "100vh", 
    overflow: "hidden" 
  },
  heroOverlay: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1,
  },
  heroContent: { 
    textAlign: "center", 
    color: "white", 
    zIndex: 2, 
    position: "relative" 
  },
  heroTitle: {
    fontSize: "3rem", 
    marginBottom: "1rem", 
    fontWeight: "bold",
    textShadow: "0 2px 4px rgba(0,0,0,0.3)",
  },
  heroSubtitle: {
    fontSize: "1.2rem", 
    opacity: 0.9, 
    textShadow: "0 1px 2px rgba(0,0,0,0.3)",
  },
  popupOverlay: {
    position: "fixed", 
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.6)",
    display: "flex", 
    justifyContent: "center", 
    alignItems: "center",
    zIndex: 1000,
  },
  popupContent: {
    backgroundColor: "#fff", 
    padding: 40, 
    borderRadius: 12,
    boxShadow: "0 20px 40px rgba(0,0,0,0.3)", 
    width: 380, 
    maxWidth: "90vw",
    position: "relative",
  },
  closeButton: {
    position: "absolute", 
    top: 15, 
    right: 20,
    background: "none", 
    border: "none", 
    fontSize: "24px", 
    cursor: "pointer",
    color: "#999", 
    width: 30, 
    height: 30,
    display: "flex", 
    alignItems: "center", 
    justifyContent: "center",
  },
  form: { 
    display: "flex", 
    flexDirection: "column" 
  },
  title: { 
    marginBottom: 20, 
    textAlign: "center", 
    color: "#333" 
  },
  input: {
    height: 40, 
    marginBottom: 15, 
    borderRadius: 4, 
    border: "1px solid #ccc",
    paddingLeft: 10, 
    fontSize: 16,
  },
  buttonGroup: { 
    display: "flex", 
    gap: 10, 
    marginTop: 5 
  },
  signupButton: {
    flex: 1, 
    height: 42, 
    backgroundColor: "#10b981", 
    color: "#fff",
    border: "none", 
    borderRadius: 4, 
    fontSize: 16, 
    cursor: "pointer",
  },
  loginButton: {
    flex: 1, 
    height: 42, 
    backgroundColor: "#2563eb", 
    color: "#fff",
    border: "none", 
    borderRadius: 4, 
    fontSize: 16, 
    cursor: "pointer",
  },
  error: { 
    marginBottom: 15, 
    color: "red", 
    fontSize: 14, 
    textAlign: "center" 
  },
};
