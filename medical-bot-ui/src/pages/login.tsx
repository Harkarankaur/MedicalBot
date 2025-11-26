// import React, { useState } from "react";

// interface LoginProps {
//   onLoginSuccess: () => void;
// }

// export default function Login({ onLoginSuccess }: LoginProps) {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error, setError] = useState("");

//   const handleSubmit = (e: React.FormEvent) => {
//     e.preventDefault();

//     // Simple validation example
//     if (!username || !password) {
//       setError("Please enter username and password.");
//       return;
//     }

//     // Fake login success (replace with your auth logic)
//     if (username === "user" && password === "pass") {
//       setError("");
//       onLoginSuccess();
//     } else {
//       setError("Invalid username or password.");
//     }
//   };

//   return (
//     <div style={styles.container}>
//       <form onSubmit={handleSubmit} style={styles.form}>
//         <h2 style={styles.title}>Login</h2>
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
//         <button type="submit" style={styles.button}>
//           Log In
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
// import React, { useState } from "react";

// interface LoginProps {
//   onLoginSuccess: () => void;
// }

// export default function Login({ onLoginSuccess }: LoginProps) {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error, setError] = useState("");
//   const [showReset, setShowReset] = useState(false);
//   const [newPassword, setNewPassword] = useState("");
//   const [confirmPassword, setConfirmPassword] = useState("");
//   const [resetMessage, setResetMessage] = useState("");

//   const handleSubmit = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!username || !password) {
//       setError("Please enter username and password.");
//       return;
//     }
//     if (username === "user" && password === "pass") {
//       setError("");
//       onLoginSuccess();
//     } else {
//       setError("Invalid username or password.");
//       setShowReset(true);
//     }
//   };

//   const handleReset = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (newPassword !== confirmPassword) {
//       setResetMessage("New passwords do not match.");
//       return;
//     }
//     // Here you would update password in your backend - this is a placeholder
//     setResetMessage("Password reset successful. Please login with your new password.");
//     setShowReset(false);
//     setPassword("");
//     setNewPassword("");
//     setConfirmPassword("");
//     setError("");
//   };

//   return (
//     <div style={styles.container}>
//       {!showReset ? (
//         <form onSubmit={handleSubmit} style={styles.form}>
//           <h2 style={styles.title}>Login</h2>
//           {error && <div style={styles.error}>{error}</div>}
//           <input
//             type="text"
//             placeholder="Username"
//             value={username}
//             onChange={(e) => setUsername(e.target.value)}
//             style={styles.input}
//           />
//           <input
//             type="password"
//             placeholder="Password"
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//             style={styles.input}
//           />
//           <button type="submit" style={styles.button}>
//             Log In
//           </button>
//         </form>
//       ) : (
//         <form onSubmit={handleReset} style={styles.form}>
//           <h2 style={styles.title}>Reset Password</h2>
//           {resetMessage && <div style={styles.error}>{resetMessage}</div>}
//           <input
//             type="password"
//             placeholder="New Password"
//             value={newPassword}
//             onChange={(e) => setNewPassword(e.target.value)}
//             style={styles.input}
//           />
//           <input
//             type="password"
//             placeholder="Confirm New Password"
//             value={confirmPassword}
//             onChange={(e) => setConfirmPassword(e.target.value)}
//             style={styles.input}
//           />
//           <button type="submit" style={styles.button}>
//             Reset Password
//           </button>
//           <button type="button" style={{...styles.button, backgroundColor: "#ccc", marginTop: 10}} onClick={() => setShowReset(false)}>
//             Cancel
//           </button>
//         </form>
//       )}
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
// import React, { useState } from "react";
// import { useNavigate } from "react-router-dom"; // Add React Router for redirect

// interface LoginProps {
//   onLoginSuccess: () => void;
// }

// export default function Login({ onLoginSuccess }: LoginProps) {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error, setError] = useState("");
//   const [showReset, setShowReset] = useState(false);
//   const [newPassword, setNewPassword] = useState("");
//   const [confirmPassword, setConfirmPassword] = useState("");
//   const [resetMessage, setResetMessage] = useState("");

//   const navigate = useNavigate();

//   const handleSubmit = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!username || !password) {
//       setError("Please enter username and password.");
//       return;
//     }
//     if (username === "user" && password === "pass") {
//       setError("");
//       onLoginSuccess();
//     } else {
//       setError("Invalid username or password.");
//       setShowReset(true);
//     }
//   };

//   const handleReset = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (newPassword !== confirmPassword) {
//       setResetMessage("New passwords do not match.");
//       return;
//     }
//     // Simulating password update success
//     setResetMessage("Password reset successful. Redirecting...");
//     setTimeout(() => {
//       setShowReset(false);
//       setPassword("");
//       setNewPassword("");
//       setConfirmPassword("");
//       setError("");
//       onLoginSuccess(); // Or any post-login success handler
//       navigate("/nextpage"); // Redirect after reset, replace "/nextpage" with actual path
//     }, 2000);
//   };

//   return (
//     <div style={styles.container}>
//       {!showReset ? (
//         <form onSubmit={handleSubmit} style={styles.form}>
//           <h2 style={styles.title}>Login</h2>
//           {error && <div style={styles.error}>{error}</div>}
//           <input
//             type="text"
//             placeholder="Username"
//             value={username}
//             onChange={(e) => setUsername(e.target.value)}
//             style={styles.input}
//           />
//           <input
//             type="password"
//             placeholder="Password"
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//             style={styles.input}
//           />
//           <button type="submit" style={styles.button}>
//             Log In
//           </button>
//         </form>
//       ) : (
//         <form onSubmit={handleReset} style={styles.form}>
//           <h2 style={styles.title}>Reset Password</h2>
//           {resetMessage && <div style={styles.error}>{resetMessage}</div>}
//           <input
//             type="password"
//             placeholder="New Password"
//             value={newPassword}
//             onChange={(e) => setNewPassword(e.target.value)}
//             style={styles.input}
//           />
//           <input
//             type="password"
//             placeholder="Confirm New Password"
//             value={confirmPassword}
//             onChange={(e) => setConfirmPassword(e.target.value)}
//             style={styles.input}
//           />
//           <button type="submit" style={styles.button}>
//             Reset Password
//           </button>
//           <button
//             type="button"
//             style={{ ...styles.button, backgroundColor: "#ccc", marginTop: 10 }}
//             onClick={() => setShowReset(false)}
//           >
//             Cancel
//           </button>
//         </form>
//       )}
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
