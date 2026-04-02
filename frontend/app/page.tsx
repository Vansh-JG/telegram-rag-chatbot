"use client";

import TelegramWorkspace from "@/components/TelegramWorkspace";

export default function Home() {
  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f8fbff_0%,#eef3ff_48%,#f8fafc_100%)] px-4 py-16 dark:bg-[linear-gradient(180deg,#020617_0%,#0f172a_48%,#111827_100%)]">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <div className="rounded-3xl border border-slate-200/80 bg-white/80 p-8 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700 dark:text-sky-300">
            Telegram Knowledge Layer
          </p>
          <h1 className="mt-3 text-3xl font-bold text-slate-900 dark:text-slate-100">
            Telegram RAG Chatbot
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Sync Telegram conversations, build a contact-aware index, and ask grounded
            questions scoped to direct messages and shared groups.
          </p>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white/85 p-6 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
          <TelegramWorkspace />
        </div>
      </div>
    </main>
  );
}
