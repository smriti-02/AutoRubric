'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getRubrics, submitSingle, submitBatch } from '@/lib/api';
import { UploadCloud, FileText, X, ArrowUpRight } from 'lucide-react';

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [files, setFiles] = useState<File[]>([]);
  const [rubricId, setRubricId] = useState('');
  const [cohortName, setCohortName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: rubrics, isLoading: isLoadingRubrics } = useQuery({ queryKey: ['rubrics'], queryFn: getRubrics });

  const singleMutation = useMutation({
    mutationFn: submitSingle,
    onSuccess: (data) => router.push(`/jobs/${data.job_id}`),
    onError: (err: Error) => setError(err.message || 'Failed to submit')
  });

  const batchMutation = useMutation({
    mutationFn: submitBatch,
    onSuccess: (data) => router.push(`/cohorts/${data.cohort_id}`),
    onError: (err: Error) => setError(err.message || 'Failed to submit batch')
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (!e.target.files) return;
    const newFiles = Array.from(e.target.files);
    
    for (const f of newFiles) {
      if (f.type !== 'application/pdf') {
        setError('Only PDF files are allowed');
        return;
      }
      if (f.size > MAX_SIZE) {
        setError(`File ${f.name} is too large. Max size is 10MB.`);
        return;
      }
    }

    setFiles([...files, ...newFiles]);
  };

  const removeFile = (idx: number) => {
    const newF = [...files];
    newF.splice(idx, 1);
    setFiles(newF);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please select at least one PDF file');
      return;
    }
    if (!rubricId) {
      setError('Please select a rubric');
      return;
    }

    if (files.length === 1) {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('rubric_id', rubricId);
      singleMutation.mutate(fd);
    } else {
      const fd = new FormData();
      files.forEach(f => fd.append('files', f));
      fd.append('rubric_id', rubricId);
      if (cohortName) fd.append('cohort_name', cohortName);
      batchMutation.mutate(fd);
    }
  };

  const isSubmitting = singleMutation.isPending || batchMutation.isPending;

  return (
    <div className="max-w-2xl mx-auto py-6">
      <div className="glass-card rounded-3xl p-8 sm:p-10 transition-all duration-300">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Upload Submissions</h1>
          <p className="text-xs text-zinc-500 mt-1">Select an active rubric and upload student PDF assignments for autonomous grading.</p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">Select Rubric</label>
            <select 
              className="w-full px-4 py-2.5 rounded-xl bg-white/70 border border-black/[0.08] text-sm text-zinc-900 focus:bg-white focus:border-zinc-900 focus:ring-4 focus:ring-zinc-900/5 outline-none transition-all duration-200 cursor-pointer disabled:opacity-50"
              value={rubricId} 
              onChange={e => setRubricId(e.target.value)}
              disabled={isLoadingRubrics}
            >
              <option value="">-- Select Rubric --</option>
              {rubrics?.map(r => (
                <option key={r.id} value={r.id}>{r.title}</option>
              ))}
            </select>
          </div>

          {files.length > 1 && (
            <div>
              <label className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">Cohort Name (Optional)</label>
              <input 
                type="text" 
                className="w-full px-4 py-2.5 rounded-xl bg-white/70 border border-black/[0.08] text-sm text-zinc-900 placeholder:text-zinc-400 focus:bg-white focus:border-zinc-900 focus:ring-4 focus:ring-zinc-900/5 outline-none transition-all duration-200" 
                value={cohortName} 
                onChange={e => setCohortName(e.target.value)} 
                placeholder="e.g. Fall 2026 Biology"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">PDF Files</label>
            <div 
              className="group border border-dashed border-black/[0.12] hover:border-zinc-900 p-8 text-center rounded-2xl bg-black/[0.01] hover:bg-black/[0.02] cursor-pointer transition-all duration-200"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const dt = new DataTransfer();
                Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
                if (fileInputRef.current) {
                  fileInputRef.current.files = dt.files;
                  handleFileChange({ target: { files: dt.files } } as unknown as React.ChangeEvent<HTMLInputElement>);
                }
              }}
            >
              <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-black/[0.04] group-hover:bg-zinc-900 group-hover:text-white flex items-center justify-center text-zinc-500 transition-colors duration-200">
                <UploadCloud className="w-5 h-5 stroke-[1.75]" />
              </div>
              <p className="text-xs font-medium text-zinc-700">Click to select or drag and drop PDFs here</p>
              <p className="text-[11px] text-zinc-400 mt-1">Maximum 10MB per file</p>
            </div>
            <input 
              type="file" 
              multiple 
              accept="application/pdf" 
              className="hidden" 
              ref={fileInputRef}
              onChange={handleFileChange}
            />
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              <span className="block text-[11px] font-medium uppercase tracking-wider text-zinc-400 ml-1">
                Selected Files ({files.length})
              </span>
              <ul className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {files.map((f, i) => (
                  <li key={i} className="flex justify-between items-center p-3 rounded-xl glass-card-subtle text-xs">
                    <div className="flex items-center gap-2.5 truncate flex-1 mr-3">
                      <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
                      <span className="truncate font-medium text-zinc-800">{f.name}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[11px] text-zinc-400">{(f.size / 1024 / 1024).toFixed(2)} MB</span>
                      <button 
                        type="button" 
                        onClick={() => removeFile(i)} 
                        className="text-zinc-400 hover:text-red-600 transition-colors p-1"
                        title="Remove file"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-2">
            <button 
              type="submit" 
              disabled={isSubmitting} 
              className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl bg-zinc-900 hover:bg-black text-white text-sm font-medium tracking-tight shadow-sm hover:shadow transition-all duration-200 disabled:opacity-50 active:scale-[0.99]"
            >
              <span>{isSubmitting ? 'Uploading...' : 'Upload and Grade'}</span>
              {!isSubmitting && <ArrowUpRight className="w-4 h-4 stroke-[2]" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
