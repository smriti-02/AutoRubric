'use client';

import { useParams } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getResult, verifyResult, getResultPdf } from '@/lib/api';
import Link from 'next/link';
import { CheckCircle2, ShieldAlert, ChevronLeft, ShieldCheck, Download } from 'lucide-react';
import dynamic from 'next/dynamic';

const PdfViewer = dynamic(
  () => import('@/components/PdfViewer').then((mod) => mod.PdfViewer),
  { ssr: false, loading: () => <div className="p-8 text-center text-xs text-zinc-400">Loading visual PDF viewer...</div> }
);

export default function ResultPage() {
  const params = useParams();
  const docId = params.doc_id as string;

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['result', docId],
    queryFn: () => getResult(docId) as Promise<{ rubric_id: string, total: number, max_total: number, needs_review: boolean, review_reasons?: string[], per_criterion?: { criterion_id: string, label: string, marks: number, credit: number, capped?: boolean, trusted: boolean, flags: { code: string, reason: string }[], evidence_bboxes: { page: number, x: number, y: number }[] }[] }>,
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyResult(docId) as Promise<{ match: boolean, differences?: unknown }>
  });

  if (isLoading) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-zinc-400">Loading grading result...</div>;
  if (error || !result) return <div className="max-w-5xl mx-auto py-12 text-center text-xs text-rose-500">Failed to load result</div>;

  return (
    <div className="max-w-5xl mx-auto py-6">
      <div className="flex items-center justify-between mb-6">
        <Link 
          href="/" 
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-900 transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </Link>
        <button 
          onClick={() => verifyMutation.mutate()} 
          disabled={verifyMutation.isPending}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full glass-card-subtle hover:bg-white text-zinc-700 text-xs font-medium transition-all shadow-sm active:scale-[0.98]"
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>{verifyMutation.isPending ? 'Verifying...' : 'Verify Score'}</span>
        </button>
      </div>

      <div className="glass-card rounded-3xl p-8 sm:p-10 mb-8 transition-all duration-300">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-8 border-b border-black/[0.05]">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Evaluation Result</span>
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 mt-1">Result for {docId}</h1>
            <p className="text-xs text-zinc-500 mt-1">Rubric ID: {result.rubric_id}</p>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-4xl font-semibold tracking-tight text-zinc-900">
              {result.total} <span className="text-xl font-normal text-zinc-400">/ {result.max_total}</span>
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mt-1">Total Score</div>
          </div>
        </div>

        {result.needs_review && (
          <div className="my-6 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-800 text-xs flex gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <h3 className="font-semibold text-amber-900">Needs Review</h3>
              <ul className="list-disc ml-4 text-amber-800 mt-1 space-y-0.5">
                {(result.review_reasons || []).map((r: string, i: number) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          </div>
        )}

        {verifyMutation.isSuccess && verifyMutation.data && (
          <div className="my-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 text-xs flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="font-semibold">Verification Proof: </span>
              {verifyMutation.data.match ? "Scores match the cryptographic evidence proof." : "Scores do not match the proof."}
            </div>
          </div>
        )}

        <div className="overflow-x-auto mt-6">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-black/[0.06] text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                <th className="py-3 px-4">Criterion</th>
                <th className="py-3 px-4">Label</th>
                <th className="py-3 px-4">Marks</th>
                <th className="py-3 px-4">Security / Trust</th>
                <th className="py-3 px-4">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {result.per_criterion?.map((c) => (
                <tr key={c.criterion_id} className={`border-b border-black/[0.04] ${!c.trusted ? 'bg-rose-500/5' : ''}`}>
                  <td className="py-4 px-4 font-medium text-xs text-zinc-900">{c.criterion_id}</td>
                  <td className="py-4 px-4">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide
                      ${c.label === 'FULL_CREDIT' ? 'bg-emerald-500/10 text-emerald-700' : 
                        c.label === 'PARTIAL_CREDIT' ? 'bg-amber-500/10 text-amber-700' : 
                        c.label === 'MISCONCEPTION' ? 'bg-purple-500/10 text-purple-700' : 
                        'bg-zinc-100 text-zinc-600'}`}>
                      {c.label}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-xs">
                    <div className="font-semibold text-zinc-900">{c.marks}</div>
                    <div className="text-[10px] text-zinc-400">Credit: {c.credit}</div>
                    {c.capped && <div className="text-[10px] text-amber-600 font-medium">Capped by dependency</div>}
                  </td>
                  <td className="py-4 px-4 text-xs">
                    {c.trusted ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Trusted
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-700">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                        Untrusted
                      </span>
                    )}
                    {c.flags && c.flags.length > 0 && (
                      <div className="mt-1 flex flex-col gap-1">
                        {c.flags.map((f, i) => (
                          <span key={i} className="text-[10px] bg-rose-500/10 text-rose-700 px-1.5 py-0.5 rounded-md font-mono" title={f.reason}>
                            {f.code}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="py-4 px-4 text-xs text-zinc-500">
                    {c.evidence_bboxes?.length > 0 ? (
                      c.evidence_bboxes.map((box, i) => (
                        <div key={i} className="text-[11px]">Page {box.page} (x:{Math.round(box.x)}, y:{Math.round(box.y)})</div>
                      ))
                    ) : (
                      <span className="text-[11px] text-zinc-400">No evidence</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 pt-8 border-t border-black/[0.05]">
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900 mb-4">Annotated PDF</h2>
          <PdfViewerWrapper docId={docId} />
        </div>
      </div>
    </div>
  );
}

function PdfViewerWrapper({ docId }: { docId: string }) {
  const { data: pdfBlob, isLoading, error } = useQuery({
    queryKey: ['resultPdf', docId],
    queryFn: () => getResultPdf(docId),
  });

  if (isLoading) return <div className="p-8 text-center text-xs text-zinc-400">Loading PDF document...</div>;
  if (error || !pdfBlob) return <div className="p-8 text-center text-xs text-rose-500">PDF not available yet or failed to load.</div>;

  const url = URL.createObjectURL(pdfBlob);

  return (
    <div className="rounded-2xl overflow-hidden border border-black/[0.06] bg-black/[0.01]">
      <PdfViewer url={url} onDownload={() => {
        const a = document.createElement('a');
        a.href = url;
        a.download = `result_${docId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }} />
    </div>
  );
}
