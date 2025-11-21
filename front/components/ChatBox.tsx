"use client";
import { useState } from "react";

type Message = {
  sender: "user" | "bot";
  text: string;
};

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

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
    <div className="p-4 bg-gray-100 h-[600px] w-[400px] flex flex-col rounded-2xl shadow-md">
      <div className="flex-1 overflow-y-auto mb-2 space-y-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-2 rounded-xl ${
              msg.sender === "user"
                ? "bg-blue-500 text-white self-end ml-auto w-fit"
                : "bg-gray-300 text-black self-start mr-auto w-fit"
            }`}
          >
            {msg.text}
          </div>
        ))}
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
          className="bg-blue-600 text-white px-4 py-2 rounded-lg"
        >
          Илгээх
        </button>
      </div>
    </div>
  );
}
