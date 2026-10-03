'use client';

import Link from "next/link";
import { useQuery } from '@tanstack/react-query';
import { getRubrics } from '@/lib/api';
import { Plus, BookOpen, ChevronRight, Layers } from 'lucide-react';

export default function DashboardPage() {
  const { data: rubrics, isLoading, error } = useQuery({ queryKey: ['rubrics'], queryFn: getRubrics });

  return (
    <div className="max-w-5xl mx-auto py-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-10 pb-6 border-b border-black/[0.05]">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Dashboard</h1>
          <p className="text-xs text-zinc-500 mt-1">Manage assessment rubrics, criteria hierarchies, and grading cohorts.</p>
        </div>
        <Link 
          href="/rubrics/new" 
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-zinc-900 hover:bg-black text-white text-xs font-medium tracking-tight shadow-sm hover:shadow transition-all duration-200 active:scale-[0.98] w-fit"
        >
          <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>Create New Rubric</span>
        </Link>
      </div>

      {/* Rubrics Section */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Available Rubrics</h2>
        <span className="text-xs text-zinc-400">{rubrics?.length || 0} Total</span>
      </div>

      {isLoading && (
        <div className="grid gap-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 rounded-2xl bg-black/[0.03] animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 text-xs">
          Failed to load rubrics.
        </div>
      )}

      {!isLoading && !error && (
        <div className="grid gap-3">
          {rubrics?.map((r) => (
            <Link
              key={r.id}
              href={`/rubrics/${r.id}`}
              className="group flex items-center justify-between p-5 rounded-2xl glass-card-subtle hover:bg-white/90 hover:border-black/[0.1] hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-black/[0.04] group-hover:bg-zinc-900 group-hover:text-white flex items-center justify-center text-zinc-600 transition-colors duration-200">
                  <BookOpen className="w-4 h-4 stroke-[2]" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-zinc-900 tracking-tight group-hover:text-black">
                    {r.title}
                  </h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="flex items-center gap-1 text-[11px] text-zinc-400">
                      <Layers className="w-3 h-3 stroke-[2]" />
                      {r.criteria?.length || 0} criteria
                    </span>
                    <span className="text-[11px] text-zinc-300">•</span>
                    <span className="text-[11px] text-zinc-400">ID: {r.id}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-400 group-hover:text-zinc-600 transition-colors hidden sm:inline">
                  View
                </span>
                <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-zinc-900 group-hover:translate-x-0.5 transition-all" />
              </div>
            </Link>
          ))}

          {(!rubrics || rubrics.length === 0) && (
            <div className="p-12 text-center rounded-3xl border border-dashed border-black/[0.08] bg-black/[0.01]">
              <p className="text-xs text-zinc-400">No rubrics found.</p>
              <Link href="/rubrics/new" className="inline-block mt-3 text-xs font-medium text-zinc-900 hover:underline">
                Create your first rubric &rarr;
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
