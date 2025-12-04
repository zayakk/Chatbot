"use client";
import { useState } from "react";

type Message = {
  sender: "user" | "bot";
  text: string;
};

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  function formatBotText(text: string) {
    const lines = text
      .split("\n")
      .filter((line) => line.trim() !== "")
      .map((line) => `<li>${line.replace(/^[-•]/, "").trim()}</li>`)
      .join("");

    return `<ul class='list-disc pl-5'>${lines}</ul>`;
  }
  
  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessage: Message = { sender: "user", text: input };
    setMessages([...messages, newMessage]);
    setInput("");

    const res = await fetch("http://localhost:8000/api/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // body: JSON.stringify({ message: input }),
      body: JSON.stringify({ message: newMessage.text }),
    });

    const data = await res.json();
    const aiMessage: Message = { sender: "bot", text: data.reply || "Error occurred" };
    setMessages((prev) => [...prev, aiMessage]);
  };
  

  return (
    <div className="p-4 bg-pink-100 h-[800px] w-[1000px] flex flex-col rounded-2xl shadow-md">
      <div className="flex-1 overflow-y-auto mb-2 space-y-2">
        <div className="flex-1 overflow-y-auto mb-2 space-y-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-2 rounded-xl max-w-[80%] ${
              msg.sender === "user"
                ? "bg-pink-500 text-white self-end ml-auto"
                : "bg-purple-200 text-black self-start"
            }`}
            dangerouslySetInnerHTML={{ __html: msg.text }}
          />
        ))}
      </div>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 border border-gray-400 rounded-lg px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Асуух зүйлээ бич..."
        />
        <button
          onClick={sendMessage}
          className="bg-pink-600 text-white px-4 py-2 rounded-lg"
        >
          Илгээх
        </button>
      </div>
    </div>
  );
}
