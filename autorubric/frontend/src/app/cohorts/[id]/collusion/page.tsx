'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getCollusion } from '@/lib/api';
import Link from 'next/link';
import { ChevronLeft, ArrowUpRight, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function CollusionPage() {
  const params = useParams();
  const cohortId = params.id as string;

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['collusion', cohortId],
    queryFn: () => getCollusion(cohortId),
  }) as { data: { doc_pairs?: { a: string, b: string, similarity: number, matching_props?: string[] }[] } | undefined, isLoading: boolean, error: unknown };

  if (isLoading) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-zinc-400">Loading collusion report...</div>;
  if (error || !report) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-rose-500">Failed to load collusion report</div>;

  const docPairs = report?.doc_pairs || [];

  return (
    <div className="max-w-5xl mx-auto py-6">
      <Link 
        href={`/cohorts/${cohortId}`} 
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-900 transition-colors mb-6"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
        <span>Back to Cohort</span>
      </Link>

      <div className="glass-card rounded-3xl p-8 sm:p-10 transition-all duration-300">
        <div className="mb-8 pb-6 border-b border-black/[0.05]">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Adversarial Integrity</span>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 mt-1">
            Collusion Report for Cohort {cohortId}
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Cross-document proposition cosine similarity matrix with greedy one-to-one alignment.
          </p>
        </div>

        {docPairs.length === 0 ? (
          <div className="p-8 text-center rounded-2xl glass-card-subtle flex flex-col items-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
            <p className="text-sm font-medium text-zinc-800">Clean Cohort</p>
            <p className="text-xs text-zinc-400 mt-1">No suspicious pairs above threshold found.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-800 text-xs flex items-center gap-2.5 font-medium">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Found {docPairs.length} suspicious pair{docPairs.length > 1 ? 's' : ''} with statistical convergence.</span>
            </div>
            
            {docPairs.map((pair: { a: string, b: string, similarity: number, matching_props?: string[] }, index: number) => (
              <div key={index} className="rounded-2xl glass-card-subtle overflow-hidden border border-black/[0.06]">
                <div className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.04] bg-black/[0.01]">
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900">
                      Pair Similarity: {(pair.similarity * 100).toFixed(1)}%
                    </h3>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      {pair.matching_props?.length || 0} matching propositions
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Link 
                      href={`/results/${pair.a}`} 
                      className="inline-flex items-center gap-1 text-xs font-medium text-zinc-600 hover:text-black transition-colors"
                    >
                      <span>View {pair.a}</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                    <span className="text-zinc-300">•</span>
                    <Link 
                      href={`/results/${pair.b}`} 
                      className="inline-flex items-center gap-1 text-xs font-medium text-zinc-600 hover:text-black transition-colors"
                    >
                      <span>View {pair.b}</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>

                <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div>
                    <span className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                      Document A ({pair.a})
                    </span>
                    <ul className="space-y-1.5 pl-2 border-l border-zinc-200">
                      {pair.matching_props?.map((m: string, i: number) => (
                        <li key={i} className="text-zinc-700 leading-relaxed">
                          {m.split('::')[0]}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                      Document B ({pair.b})
                    </span>
                    <ul className="space-y-1.5 pl-2 border-l border-zinc-200">
                      {pair.matching_props?.map((m: string, i: number) => (
                        <li key={i} className="text-zinc-700 leading-relaxed">
                          {m.split('::')[1]}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
