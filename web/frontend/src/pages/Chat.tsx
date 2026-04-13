import { useEffect, useRef, useState, useCallback } from "react";
import { Send, Bot, User, Loader2, WifiOff } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [connected, setConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking, scrollToBottom]);

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

      socket.onopen = () => setConnected(true);

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const content = data.message ?? data.content ?? event.data;
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content, timestamp: new Date() },
          ]);
          setThinking(false);
        } catch {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: event.data, timestamp: new Date() },
          ]);
          setThinking(false);
        }
      };

      socket.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        setConnected(false);
        socket.close();
      };

      ws.current = socket;
    };

    connect();
    return () => ws.current?.close();
  }, []);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, timestamp: new Date() },
    ]);
    ws.current.send(JSON.stringify({ message: text }));
    setInput("");
    setThinking(true);
    inputRef.current?.focus();
  };

  return (
    <div className="animate-fade-in flex h-[calc(100vh-8rem)] flex-col rounded-xl border border-gray-800 bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-accent" />
          <span className="text-sm font-semibold text-gray-200">
            JobPilot Assistant
          </span>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 text-xs ${
            connected ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {connected ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
              Connected
            </>
          ) : (
            <>
              <WifiOff className="h-3 w-3" />
              Disconnected
            </>
          )}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && !thinking && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-500">
            <Bot className="h-12 w-12 opacity-30" />
            <p className="text-sm">
              Start a conversation with your JobPilot assistant
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`flex max-w-[75%] gap-3 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                  msg.role === "user"
                    ? "bg-accent/20 text-accent"
                    : "bg-gray-800 text-gray-400"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="h-4 w-4" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
              </div>
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-accent text-white"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                {msg.content}
              </div>
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-800 text-gray-400">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2 rounded-2xl bg-gray-800 px-4 py-2.5 text-sm text-gray-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                Thinking...
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={sendMessage}
        className="flex items-center gap-3 border-t border-gray-800 px-5 py-4"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            connected ? "Type a message..." : "Connecting..."
          }
          disabled={!connected}
          className="flex-1 rounded-xl border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-200 outline-none placeholder:text-gray-600 focus:border-accent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!connected || !input.trim()}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-white transition-colors hover:bg-accent-hover disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
