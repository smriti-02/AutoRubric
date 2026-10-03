'use client';

import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCohort, getJob, retryJob } from '@/lib/api';
import Link from 'next/link';
import { CohortHeatmap } from '@/components/Heatmap';
import { Job } from '@/lib/api/schemas';
import { ChevronLeft, ArrowUpRight, RefreshCw, FileText, ShieldAlert } from 'lucide-react';

const STAGES = ['QUEUED', 'EXTRACTING', 'SEGMENTING', 'RETRIEVING', 'EVALUATING', 'AUDITING', 'SCORING', 'ANNOTATING', 'DONE'];

function JobRow({ jobInitial }: { jobInitial: Job & { file_name?: string } }) {
  const queryClient = useQueryClient();
  const { data: job } = useQuery({
    queryKey: ['job', jobInitial.job_id],
    queryFn: () => getJob(jobInitial.job_id),
    initialData: jobInitial,
    refetchInterval: (query) => {
      const state = query.state.data;
      if (!state) return 2000;
      const term = ['DONE', 'FAILED', 'NEEDS_REVIEW'].includes(state.status);
      return term ? false : 2000;
    }
  });

  const retryMutation = useMutation({
    mutationFn: () => retryJob(jobInitial.job_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job', jobInitial.job_id] })
  });

  const currentStatus = job?.status || jobInitial.status;
  const currentStageIdx = STAGES.indexOf(currentStatus);
  const isFailed = currentStatus === 'FAILED';
  const needsReview = currentStatus === 'NEEDS_REVIEW';
  const isDone = currentStatus === 'DONE';

  return (
    <tr className="border-b border-black/[0.04] hover:bg-black/[0.01] transition-colors">
      <td className="py-4 px-4">
        <div className="flex items-center gap-2.5">
          <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
          <span className="text-xs font-medium text-zinc-900">{jobInitial.file_name}</span>
          {needsReview && (
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 border border-amber-500/20">
              <ShieldAlert className="w-2.5 h-2.5" />
              NEEDS_REVIEW
            </span>
          )}
        </div>
      </td>
      <td className="py-4 px-4">
        <span className={`inline-block text-[11px] font-semibold tracking-wide px-2.5 py-1 rounded-full ${
          isFailed 
            ? 'bg-rose-500/10 text-rose-700' 
            : isDone 
            ? 'bg-emerald-500/10 text-emerald-700' 
            : needsReview 
            ? 'bg-amber-500/10 text-amber-700' 
            : 'bg-blue-500/10 text-blue-700'
        }`}>
          {currentStatus}
        </span>
        {isFailed && job?.error && <div className="text-rose-600 text-[11px] mt-1">{job.error}</div>}
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center gap-1" title={currentStatus}>
          {STAGES.map((s, i) => {
            const active = i <= currentStageIdx;
            return (
              <div 
                key={s} 
                className={`h-1.5 w-3.5 rounded-full transition-all duration-300 ${
                  active 
                    ? isDone 
                      ? 'bg-emerald-500' 
                      : 'bg-zinc-900' 
                    : 'bg-black/[0.06]'
                }`}
                title={s} 
              />
            );
          })}
        </div>
      </td>
      <td className="py-4 px-4 text-right">
        {isDone && job?.doc_id && (
          <Link 
            href={`/results/${job.doc_id}`} 
            className="inline-flex items-center gap-1 text-xs font-medium text-zinc-900 hover:text-black hover:underline"
          >
            <span>View Result</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        )}
        {needsReview && job?.doc_id && (
          <Link 
            href={`/results/${job.doc_id}`} 
            className="inline-flex items-center gap-1 text-xs font-medium text-amber-800 hover:underline"
          >
            <span>Review Result</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        )}
        {isFailed && (
          <button 
            onClick={() => retryMutation.mutate()} 
            disabled={retryMutation.isPending} 
            className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1 rounded-full bg-black/[0.04] hover:bg-black/[0.08] text-zinc-700 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${retryMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{retryMutation.isPending ? 'Retrying...' : 'Retry'}</span>
          </button>
        )}
      </td>
    </tr>
  );
}

export default function CohortPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: cohort, isLoading, error } = useQuery({
    queryKey: ['cohort', id],
    queryFn: () => getCohort(id),
  }) as { data: { name?: string, jobs: (Job & { file_name?: string })[] } | undefined, isLoading: boolean, error: unknown };

  if (isLoading) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-zinc-400">Loading cohort...</div>;
  if (error || !cohort) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-rose-500">Failed to load cohort</div>;

  return (
    <div className="max-w-5xl mx-auto py-6">
      <Link 
        href="/" 
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-900 transition-colors mb-6"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
        <span>Back to Dashboard</span>
      </Link>

      <div className="glass-card rounded-3xl p-8 sm:p-10 mb-8 transition-all duration-300">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-black/[0.05]">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Grading Cohort</span>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 mt-1">Cohort: {cohort.name || id}</h1>
            <p className="text-xs text-zinc-500 mt-1">Real-time asynchronous job tracking across all submission pipeline stages.</p>
          </div>
          <Link 
            href={`/cohorts/${id}/collusion`} 
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-zinc-900 hover:bg-black text-white text-xs font-medium tracking-tight shadow-sm hover:shadow transition-all duration-200 active:scale-[0.98] w-fit"
          >
            <span>View Collusion Report</span>
            <ArrowUpRight className="w-3.5 h-3.5 stroke-[2]" />
          </Link>
        </div>

        {cohort.jobs && <CohortHeatmap jobs={cohort.jobs} />}
        
        <div className="overflow-x-auto mt-6">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-black/[0.06] text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                <th className="py-3 px-4">File Name</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Pipeline Stages</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {cohort.jobs?.map((job) => (
                <JobRow key={job.job_id} jobInitial={job} />
              ))}
              {(!cohort.jobs || cohort.jobs.length === 0) && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-xs text-zinc-400">
                    No submissions found in this cohort.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
