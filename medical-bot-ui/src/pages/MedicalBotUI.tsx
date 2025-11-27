import React, { useState, useEffect, useRef } from "react";
import {
  SendHorizonal,Mic,PlusCircle,Sun,Moon,Menu,Search,SquarePen,Settings,User,Copy,ThumbsUp,ThumbsDown,Share2,Clock,
} 
from "lucide-react";

type Message = { sender: string; text: string; time: string ;route?: string};
type Chat = { id: number; title: string; messages: Message[] };
type UserProfile = { name: string; email: string; id: string };

export default function MedicalBotUI() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showAccount, setShowAccount] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  /* ---------------- HEADER SEARCH STATES ---------------- */
  const [headerSearchOpen, setHeaderSearchOpen] = useState(false);
  const [headerSearchValue, setHeaderSearchValue] = useState("");
  const searchRef = useRef<any>(null);

  // const [userProfile] = useState<UserProfile>({
  //   name: "John Doe",
  //   email: "john@example.com",
  //   id: "USR123456",
  // });

  // ✅ NEW - loads from localStorage
const [userProfile, setUserProfile] = useState<UserProfile>({
  name: localStorage.getItem("username") || "Guest",
  email: localStorage.getItem("email") || "No email",
  id: localStorage.getItem("password") ? "Authenticated" : "Not logged in", // Hide password, show status
});

  const recognitionRef = useRef<any>(null);
  const endRef = useRef<any>(null);

  const currentChat = chats.find((c) => c.id === activeChat);
  const [botProcessing, setBotProcessing] = useState(false);


  
  /* -------------------- EFFECTS -------------------- */
  function getHighlightedText(text: string, highlight: string) {
    if (!highlight) return text;
    const regex = new RegExp(`(${highlight})`, "gi");
    const parts = text.split(regex);
    return (
      <span>
        {parts.map((part, i) =>
          part.toLowerCase() === highlight.toLowerCase() ? (
            <span key={i} style={{ backgroundColor: "yellow" }}>
              {part}
            </span>
          ) : (
            part
          )
        )}
      </span>
    );
  }

  useEffect(() => {
  // Load real signup data
  const username = localStorage.getItem("username") || "Guest";
  const email = localStorage.getItem("email") || "No email set";
  setUserProfile({
    name: username,
    email: email,
    id: localStorage.getItem("password") ? "Active User" : "Not logged in",
  });
}, []);
  useEffect(() => {
    const handleResize = () => setSidebarOpen(window.innerWidth > 768);
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  /* Close header search when clicking outside */
  useEffect(() => {
    function handleClickOutside(e: any) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setHeaderSearchOpen(false);
        setHeaderSearchValue("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    speechSynthesis.cancel();
    const msg = new SpeechSynthesisUtterance("How can I help you?");
    msg.lang = "en-US";
    speechSynthesis.speak(msg);
    return () => speechSynthesis.cancel();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentChat?.messages, botProcessing]);

  /* -------------------- CHAT FUNCTIONS -------------------- */

  const createNewChat = () => {
    const newChatId = Date.now();
    setActiveChat(newChatId);
  };

  const sendMessage = () => {
  if (!input.trim()) return;

  const timeString = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  // 👇 capture the current text once
  const userText = input;

  const userMsg: Message = {
    sender: "user",
    text: userText,
    time: timeString,
  };

  if (!currentChat) {
    // safer: create a new ID if none exists
    const newChatId = activeChat ?? Date.now();

    const newChat: Chat = {
      id: newChatId,
      title: userText.length > 25 ? userText.slice(0, 25) + "..." : userText,
      messages: [userMsg],
    };

    setActiveChat(newChatId);
    setChats((prev) => [newChat, ...prev]);
    setInput("");
    setBotProcessing(true);

    // 👇 pass the text to addBotReply
    setTimeout(() => addBotReply(newChatId, userText), 1200);
    return;
  }

  setChats((prevChats) =>
    prevChats.map((chat) =>
      chat.id === activeChat
        ? { ...chat, messages: [...chat.messages, userMsg] }
        : chat
    )
  );

  setInput("");
  setBotProcessing(true);

  if (activeChat !== null) {
    // 👇 pass the text to addBotReply
    setTimeout(() => addBotReply(activeChat, userText), 1200);
  }
};

const addBotReply = async (chatId: number, userText: string) => {
  try {
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // 👇 send the text we got from sendMessage
      body: JSON.stringify({ message: userText }),
    });

    const data = await res.json();

    const botMsg: Message = {
      sender: "bot",
      text: data.reply,
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      route: data.route
    };

    setChats((prevChats) =>
      prevChats.map((c) =>
        c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c
      )
    );
  } catch (err) {
    console.error(err);
    const botMsg: Message = {
      sender: "bot",
      text: "Sorry, something went wrong.",
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };
    setChats((prevChats) =>
      prevChats.map((c) =>
        c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c
      )
    );
  } finally {
    setBotProcessing(false);
  }
};


  /* -------------------- VOICE INPUT -------------------- */

  const startVoice = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice recognition not supported.");
      return;
    }

    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.lang = "en-US";
    recognitionRef.current.onresult = (e: any) => {
      setInput(e.results[0][0].transcript);
    };
    recognitionRef.current.start();
  };

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  /* -------------------- THEME COLORS -------------------- */

  const bgColor = theme === "light" ? "#ffffff" : "#0d1117";
  const textColor = theme === "light" ? "#000" : "#e6edf3";
  const sidebarBg = theme === "light" ? "#f3f4f6" : "#161b22";
  const headerBg = theme === "light" ? "#f9fafb" : "#161b22";
  const borderColor = theme === "light" ? "#e5e7eb" : "#30363d";
  const activeChatBg = theme === "light" ? "#dbeafe" : "#1f2937";
  const popOutBg = theme === "light" ? "#ffffff" : "#2c2c31";
  const popOutText = theme === "light" ? "#000" : "#fff";

  const buttonStyle = {
    background: theme === "light" ? "#f3f4f6" : "#161b22",
    color: theme === "light" ? "#161b22" : "#e6edf3",
    padding: "10px",
    borderRadius: "8px",
    border: `1px solid ${borderColor}`,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    width: "85%",
    margin: "10px auto",
  };

  const inputStyle = {
    background: theme === "light" ? "#ffffff" : "#0d1117",
    color: theme === "light" ? "#000" : "#fff",
    padding: "10px 14px",
    borderRadius: "25px",
    border: `1px solid ${borderColor}`,
    fontSize: "14px",
    width: "85%",
    margin: "10px auto",
  };

  /* -------------------- SIDEBAR -------------------- */

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        width: "100vw",       // added
        maxWidth: "100vw",    // added
        margin: 0,            // added
        overflow: "hidden",   // added
        background: bgColor,
        color: textColor,
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          width: sidebarOpen ? "220px" : "45px",
          background: sidebarBg,
          borderRight: `1px solid ${borderColor}`,
          display: "flex",
          flexDirection: "column",
          transition: "width 0.25s ease",
        }}
      >
        
        {/* Hamburger */}
        <div
          style={{
            display: "flex",
            justifyContent:  "space-between",
            padding: "10px",
          }}
        >
          {sidebarOpen && (
            <PlusCircle
              size={22}
              style={{ cursor: "pointer", marginTop: 5 }}
              onClick={createNewChat} // optional: same as new chat button
        />
        )}
          <Menu
            size={20}
            onClick={toggleSidebar}
            style={{ cursor: "pointer", marginTop: 5 }}
          />
        </div>

        {/* FULL SIDEBAR */}
        {sidebarOpen ? (
          <>
            <button onClick={createNewChat} style={buttonStyle}>
              <SquarePen size={18} /> New Chat
            </button>

            <input
              type="text"
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value.toLowerCase())}
              style={inputStyle}
            />

            {/* Search dropdown */}
            {searchQuery && (
              <div
                style={{
                  background: bgColor,
                  border: `1px solid ${borderColor}`,
                  borderRadius: 8,
                  maxHeight: "150px",
                  overflowY: "auto",
                  width: "85%",
                  margin: "0 auto 10px",
                }}
              >
                {chats
                  .filter((chat) =>
                    chat.title.toLowerCase().includes(searchQuery)
                  )
                  .map((chat) => (
                    <div
                      key={chat.id}
                      style={{
                        padding: "8px 12px",
                        cursor: "pointer",
                      }}
                      onClick={() => {
                        setActiveChat(chat.id);
                        setSearchQuery("");
                      }}
                    >
                      {chat.title}
                    </div>
                  ))}
              </div>
            )}

            <div
              style={{
                fontWeight: 300,
                fontSize: "14px",
                marginLeft: "15px",
                marginTop: "10px",
              }}
            >
              Your Chats...
            </div>

            {/* Chat History */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                marginTop: "5px",
                padding: "0 10px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => setActiveChat(chat.id)}
                  style={{
                    padding: "10px",
                    borderRadius: 8,
                    cursor: "pointer",
                    background:
                      activeChat === chat.id ? activeChatBg : "transparent",
                    border:
                      activeChat === chat.id
                        ? `1px solid #2563eb`
                        : `1px solid ${borderColor}`,
                  }}
                >
                  {chat.title}
                </div>
              ))}
            </div>

            {/* Account + Settings */}
            <div
              style={{
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                }}
                onClick={() => setShowAccount(true)}
              >
                <User size={16} /> Account
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                }}
                onClick={() => setShowSettings(true)}
              >
                <Settings size={16} /> Settings
              </div>
            </div>
          </>
        ) : (
          /* COLLAPSED SIDEBAR */
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              alignItems: "center",
              paddingTop: "10px",
            }}
          >
          <div />

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "1.2rem",
                alignItems: "center",
                marginBottom: "14px",
              }}
            >

              <User
                size={20}
                style={{ cursor: "pointer" }}
                onClick={() => setShowAccount(true)}
              />

              <Settings
                size={20}
                onClick={() => setShowSettings(true)}
                style={{ cursor: "pointer", marginBottom: 10 }}
              />
            </div>
          </div>
        )}
      </div>

      {/* -------------------- MAIN CHAT AREA -------------------- */}

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          position: "relative",
          background: bgColor,
          color: textColor,
        }}
      >
        {/* ACCOUNT POPUP */}
        {showAccount && (
          <div
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 300,
              background: popOutBg,
              color: popOutText,
              padding: 20,
              borderRadius: 8,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              zIndex: 1000,
              textAlign: "center",
            }}
          >
            <h3> {userProfile.name}</h3>
            <p>{userProfile.id}</p>
            <button
              style={{
                marginTop: 10,
                padding: "8px 16px",
                borderRadius: 20,
                border: "none",
                cursor: "pointer",
                background: "#2563eb",
                color: "#fff",
              }}
              onClick={() => setShowAccount(false)}
            >
              Close
            </button>
          </div>
        )}

        {/* SETTINGS POPUP */}
        {showSettings && (
          <div
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 320,
              background: popOutBg,
              color: popOutText,
              padding: 20,
              borderRadius: 8,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              zIndex: 1000,
              textAlign: "center",
            }}
          >
            <h3>User Profile</h3>
            <p><strong>Username:</strong> {userProfile.name}</p>
            <p><strong>Email:</strong> {userProfile.email}</p>
            <p><strong>Status:</strong> {userProfile.id}</p>

            <div style={{ margin: "10px 0" }}>
              {theme === "light" ?  (
                <button
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    background: "#0d1117",
                    color: "#fff",
                  }}
                  onClick={() => setTheme("light")}
                >
                  Dark Mode
                </button>
              ):(
                <button
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    background: "#f3f4f6",
                  }}
                  onClick={() => setTheme("dark")}
                >
                  Light Mode
                </button>
                
              ) }
            </div>
            <button
              style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    background: "#f3f4f6",
                }}
              onClick={() => {
              if (window.confirm("Are you sure you want to delete all chat history?")) {
              setChats([]);
              setActiveChat(null);
              setShowSettings(false);
              }
              }}
              >
              Delete History
              </button>

            {/* Logout */}
            <button
              style={{
                display: "block",
                width: "100%",
                marginTop: "10px auto 0",
                padding: "10px 16px",
                borderRadius: 20,
                border: "none",
                cursor: "pointer",
                background: "#0f0101ff",
                color: "#f9f4f4ff",
                


              }}
              onClick={() => {
    localStorage.clear(); // ✅ Clears ALL signup data
    setUserProfile({ name: "Guest", email: "No email", id: "Not logged in" });
    alert("Logged out - all data cleared!");
  }}
            >
              Logout
            </button>

            {/* Close */}
            <button
              style={{
                display: "block",
                width: "100%",marginTop: 10,
                padding: "10px 16px",
                borderRadius: 20,
                border: "none",
                cursor: "pointer",
                background: "#464ef0ff",
                color: "#fff",
              }}
              onClick={() => setShowSettings(false)}
            >
              Close
            </button>
          </div>
        )}

        {/* MAIN CHAT UI */}
        {!showAccount && !showSettings && (
          <>
            {/* Header */}
            <div
              style={{
                padding: "10px 10px",
                borderBottom: `1px solid ${borderColor}`,
                fontWeight: 600,
                fontSize: "18px",
                background: headerBg,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  fontSize: "20px",
                  gap: "8px",
                }}
              >
                <PlusCircle size={20} /> Medicare
              </div>

              {/* HEADER SEARCH + ACCOUNT ICONS */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                }}
                ref={searchRef}
              >
                
                <SquarePen size={18}
                  style={{ cursor: "pointer" }}
                  onClick={createNewChat}
                />
                {/* SEARCH ICON */}
                <Search
                  size={20}
                  style={{ cursor: "pointer" }}
                  onClick={() => setHeaderSearchOpen((p) => !p)}
                />

                {/* SEARCH INPUT */}
                {headerSearchOpen && (
                  <input
                    autoFocus
                    type="text"
                    placeholder="Search this chat..."
                    value={headerSearchValue}
                    onChange={(e) =>
                      setHeaderSearchValue(e.target.value.toLowerCase())
                    }
                    style={{
                      padding: "6px 12px",
                      borderRadius: "20px",
                      border: `1px solid ${borderColor}`,
                      background: theme === "light" ? "#fff" : "#0d1117",
                      color: textColor,
                      width: "180px",
                      transition: "0.2s",
                    }}
                  />
                )}

                {/* THEME */}
                {theme === "light" ? (
                  <Moon
                    size={20}
                    style={{ cursor: "pointer" }}
                    onClick={() => setTheme("dark")}
                  />
                ) : (
                  <Sun
                    size={20}
                    style={{ cursor: "pointer" }}
                    onClick={() => setTheme("light")}
                  />
                )}
              </div>
            </div>

            {/* Chat Area */}
            <div
              style={{
                flex: 1,
                padding: "20px",
                overflowY: "auto",
              }}
            >
              {chats.length === 0 && (
                <div
                  style={{
                    width: "100%",
                    textAlign: "center",
                    marginTop: "120px",
                    opacity: 0.8,
                  }}
                >
                  <div style={{ fontSize: "30px", marginBottom: "12px" }}>
                    Hii 👋
                  </div>
                  <div style={{ fontSize: "30px" }}>How can I help you ?</div>
                </div>
              )}
{currentChat?.messages
  ?.filter((msg) =>
    headerSearchValue
      ? msg.text.toLowerCase().includes(headerSearchValue)
      : true
  )
  .map((msg, i) => {

    return (
      <div
        key={i}
        style={{
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
          marginBottom: "6px",
        }}
      >

{msg.sender === "bot" ? (() => {
  const lines = msg.text.split("\n");
  const delimiters = /[,]/; // comma, dash, or slash
  const delimiter = /[-]/;
  const delimiteer = /[\-\/*():]/;
  const isMultiLine = lines.length > 1;
  const anyLineHasMultipleColumns = lines.some(line => line.split(delimiter).length > 1);
  const isSingleLineMultipleColumns = !isMultiLine && msg.text.split(delimiters).length > 2;
  const hasMultiLineDelimiters = lines.some(line => 
    (line.match(delimiteer) || []).length > 0
  );
  if (isMultiLine && anyLineHasMultipleColumns ) {
    // Multi-line with delimiters -> table
    const rowColumns = lines.map(line =>
      line.split(delimiter).map(cell => cell.trim())
    );
    const maxCols = Math.max(...rowColumns.map(cols => cols.length));
    return (
      <div style={{
        width: "auto",
        height:"auto",
        maxWidth: "800px",
        maxHeight: "600px",
        overflowX: "auto",
        overflowY: "auto",
        border: theme === "light" ? "1px solid #ccc" : "1px solid #444",
        borderRadius: "8px",
        boxShadow: theme === "light" ? "0 1px 3px rgba(0,0,0,0.1)" : "0 2px 6px rgba(0,0,0,0.7)"
      }}>
        <table style={{
          borderCollapse: "collapse",
          borderSpacing: "0",
          tableLayout: "auto",
          width: "100%",
          maxWidth: "max-content",
          borderRadius: "8px",
          overflow: "hidden",
          boxShadow: theme === "light" ? "0 1px 3px rgba(0,0,0,0.1)" : "0 2px 6px rgba(0,0,0,0.7)"
        }}>
          <thead style={{ background: theme === "light" ? "#2563EB" : "#111827", color: "#fff" }}>
            <tr>
              <th style={{ padding: "8px 12px", textAlign: "center" }}>SNo.</th>
              {Array.from({ length: maxCols }).map((_, idx) => (
                <th key={idx} style={{ padding: "8px 12px" }}>{`Column ${idx + 1}`}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowColumns.map((cols, idx) => (
              <tr key={idx}
                style={{
                  padding: "8px 12px",
                  textAlign: "center",
                  background: idx % 2 === 0 ? (theme === "light" ? "#F3F4F6" : "#1E1E2A") : "transparent",
                  color: theme === "light" ? "#111" : "#E6EDF3",
                  border: theme === "light" ? "1px solid #D1D5DB" : "1px solid #3F3F46"
                }}
                onMouseEnter={e => e.currentTarget.style.background = theme === "light" ? "#DBEAFE" : "#2C2C31"}
                onMouseLeave={e => e.currentTarget.style.background = idx % 2 === 0 ? (theme === "light" ? "#F3F4F6" : "#1C1F26") : "transparent"}
              >
                <td style={{ padding: "8px 12px" }}>{idx + 1}</td>
                {Array.from({ length: maxCols }).map((_, cidx) => (
                  <td key={cidx} style={{ padding: "8px 12px", wordBreak: "break-word", textAlign: "left" }}>
                    {cols[cidx] || ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  if (isMultiLine && hasMultiLineDelimiters ) {
  // Always render messages from "rag" route as bubbles
  return (
    <div
      style={{
        background: theme === "light" ? "#E5E7EB" : "#30363D",
        color: textColor,
        padding: "10px 12px",
        borderRadius: "12px",
        maxWidth: "70%",
        whiteSpace: "pre-wrap",
        boxShadow: theme === "light" ? "0 1px 2px rgba(0,0,0,0.1)" : "0 1px 2px rgba(0,0,0,0.5)",
      }}
    >
      {getHighlightedText(msg.text, headerSearchValue)}
    </div>
  );
}
  if (isSingleLineMultipleColumns) {
    // Single line multiple columns -> table with single column rows
    const rows = msg.text.split(delimiters).map(cell => cell.trim());
    return (
      <div style={{
        width: "100%",
        maxWidth: "600px",
        height: "300px",
        overflowY: "auto",
        border: theme === "light" ? "1px solid #ccc" : "1px solid #444",
        borderRadius: "8px",
        boxShadow: theme === "light" ? "0 1px 3px rgba(0,0,0,0.1)" : "0 2px 6px rgba(0,0,0,0.7)"
      }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          borderSpacing: 0,
          boxShadow: theme === "light" ? "0 1px 3px rgba(0,0,0,0.1)" : "0 2px 6px rgba(0,0,0,0.7)"
        }}>
          <thead style={{ background: theme === "light" ? "#2563EB" : "#111827", color: "#fff" }}>
            <tr>
              <th style={{ padding: "8px 12px", textAlign: "center" }}>SNo.</th>
              <th style={{ padding: "8px 12px" }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((cell, idx) => (
              <tr key={idx}
                style={{
                  background: idx % 2 === 0 ? (theme === "light" ? "#F3F4F6" : "#1E1E2A") : "transparent",
                  color: theme === "light" ? "#111" : "#E6EDF3",
                  border: theme === "light" ? "1px solid #D1D5DB" : "1px solid #3F3F46"
                }}
                onMouseEnter={e => e.currentTarget.style.background = theme === "light" ? "#DBEAFE" : "#2C2C31"}
                onMouseLeave={e => e.currentTarget.style.background = idx % 2 === 0 ? (theme === "light" ? "#F3F4F6" : "#1C1F26") : "transparent"}
              >
                <td style={{ padding: "8px 12px", textAlign: "center" }}>{idx + 1}</td>
                <td style={{ padding: "8px 12px", wordBreak: "break-word" }}>{cell}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  // Else normal message bubble
  return (
    <div
      style={{
        background:  theme === "light" ? "#E5E7EB" : "#30363D",
        color:  textColor,
        padding: "10px 12px",
        borderRadius: "12px",
        maxWidth: "70%",
        whiteSpace: "pre-wrap",
        boxShadow: theme === "light" ? "0 1px 2px rgba(0,0,0,0.1)" : "0 1px 2px rgba(0,0,0,0.5)",
      }}
    >
      {getHighlightedText(msg.text, headerSearchValue)}
    </div>
  );
})() : (
  // user message rendering
  <div
    style={{
      background: "#2563EB",
      color: "#fff",
      padding: "10px 12px",
      borderRadius: "12px",
      maxWidth: "70%",
      whiteSpace: "pre-wrap",
      boxShadow: theme === "light" ? "0 1px 2px rgba(0,0,0,0.1)" : "0 1px 2px rgba(0,0,0,0.5)",
      alignSelf: "flex-end",
    }}
  >
    {getHighlightedText(msg.text, headerSearchValue)}
  </div>
)}


        <div
          style={{
            fontSize: "12px",
            color: theme === "light" ? "#555" : "#9ca3af",
            marginTop: "2px",
          }}
        >
          {msg.time}
        </div>
      </div>
    );
  })}

              {botProcessing && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    margin: "10px 0",
                  }}
                >
                  <div
                    style={{
                      width: "12px",
                      height: "12px",
                      borderRadius: "50%",
                      background:
                        theme === "light" ? "#2563eb" : "#e6edf3",
                      animation: "pulse 1s infinite",
                      marginRight: "10px",
                    }}
                  ></div>
                </div>
              )}

              <div ref={endRef} />
            </div>

            {/* Input */}
            <div
              style={{
                display: "flex",
                padding: "8px 12px",
                borderTop: `1px solid ${borderColor}`,
                gap: "10px",
                alignItems: "center",
              }}
            >
              <textarea
                placeholder="Ask your query..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }else if (e.key === "Enter" && e.shiftKey) {
                  // Insert a newline at the cursor position
                  e.preventDefault();
                  setInput((prev) => prev + "\n");
                  }
                }}
                style={{
                  flex: 1,
                  padding: "6px 15px",
                  borderRadius: "25px",
                  border: `1px solid ${borderColor}`,
                  background: theme === "light" ? "#fff" : "#0d1117",
                  color: textColor,
                  fontSize: "18px",      
                  fontFamily:"Arial, sans-serif",
                }}
              />
              <SendHorizonal
                size={20}
                onClick={sendMessage}
                style={{ cursor: "pointer" }}
              />
              <Mic
                size={20}
                onClick={startVoice}
                style={{ cursor: "pointer" }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}



