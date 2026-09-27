"use client";

import React, { useState } from "react";
import "./globals.css";
import { AuthRoleProvider } from "@/context/AuthRoleContext";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { AlertCenter } from "@/components/layout/AlertCenter";
import { useSSEStream } from "@/hooks/useSSEStream";

function AppShell({ children }: { children: React.ReactNode }) {
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const { isConnected, status, source, events, lastHeartbeat, clearEvents } = useSSEStream();

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Navbar
        onToggleAlerts={() => setIsAlertsOpen(!isAlertsOpen)}
        unreadCount={events.length}
        sseStatus={status}
        sseSource={source}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          {children}
        </main>
      </div>
      <AlertCenter
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        events={events}
        onClear={clearEvents}
        status={status}
        source={source}
        lastHeartbeat={lastHeartbeat}
      />
    </div>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-blue-500/30 selection:text-blue-200">
        <AuthRoleProvider>
          <AppShell>{children}</AppShell>
        </AuthRoleProvider>
      </body>
    </html>
  );
}
