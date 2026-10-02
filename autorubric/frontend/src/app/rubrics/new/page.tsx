'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { createRubric } from '@/lib/api';
import { Criterion } from '@/lib/api/schemas';
import { Plus, Trash2, ChevronLeft, ArrowRight, Layers } from 'lucide-react';
import Link from 'next/link';

export default function NewRubricPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [criteria, setCriteria] = useState<Criterion[]>([
    { id: 'c1', description: '', weight: 1.0, depends_on: [] }
  ]);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createRubric,
    onSuccess: () => {
      router.push('/');
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create rubric');
    }
  });

  const hasCycle = (crit: Criterion[]) => {
    const adj = new Map<string, string[]>();
    crit.forEach(c => adj.set(c.id, c.depends_on || []));
    
    const visited = new Set<string>();
    const recStack = new Set<string>();

    const dfs = (node: string): boolean => {
      if (!visited.has(node)) {
        visited.add(node);
        recStack.add(node);
        
        for (const neighbor of adj.get(node) || []) {
          if (!visited.has(neighbor) && dfs(neighbor)) return true;
          else if (recStack.has(neighbor)) return true;
        }
      }
      recStack.delete(node);
      return false;
    };

    for (const node of adj.keys()) {
      if (dfs(node)) return true;
    }
    return false;
  };

  const validate = () => {
    setError(null);
    if (!title) return 'Title is required';
    if (criteria.length === 0) return 'At least one criterion is required';
    
    const ids = new Set<string>();
    for (const c of criteria) {
      if (!c.id) return 'Criterion ID cannot be empty';
      if (ids.has(c.id)) return `Duplicate ID: ${c.id}`;
      ids.add(c.id);
      if (c.weight <= 0) return `Weight must be positive for ${c.id}`;
    }

    for (const c of criteria) {
      for (const dep of (c.depends_on || [])) {
        if (!ids.has(dep)) return `Dependency ${dep} for ${c.id} does not exist`;
      }
    }

    if (hasCycle(criteria)) {
      return 'Cycle detected in dependencies';
    }

    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const valError = validate();
    if (valError) {
      setError(valError);
      return;
    }
    mutation.mutate({ title, criteria });
  };

  const addCriterion = () => {
    const nextId = `c${criteria.length + 1}`;
    setCriteria([...criteria, { id: nextId, description: '', weight: 1.0, depends_on: [] }]);
  };

  const removeCriterion = (index: number) => {
    const newC = [...criteria];
    newC.splice(index, 1);
    setCriteria(newC);
  };

  const updateCriterion = (index: number, field: keyof Criterion, value: Criterion[keyof Criterion]) => {
    const newC = [...criteria];
    newC[index] = { ...newC[index], [field]: value };
    setCriteria(newC);
  };

  return (
    <div className="max-w-3xl mx-auto py-6">
      <Link 
        href="/" 
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-900 transition-colors mb-6"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
        <span>Back to Dashboard</span>
      </Link>

      <div className="glass-card rounded-3xl p-8 sm:p-10 transition-all duration-300">
        <div className="mb-8 pb-6 border-b border-black/[0.05]">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">Rubric Specification</span>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 mt-1">Create New Rubric</h1>
          <p className="text-xs text-zinc-500 mt-1">Define assessment title, weighted criteria, and DAG dependency requirements.</p>
        </div>

        {error && (
          <div className="mb-6 p-3.5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-medium">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-8">
          <div>
            <label className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">Title</label>
            <input 
              type="text" 
              className="w-full px-4 py-2.5 rounded-xl bg-white/70 border border-black/[0.08] text-sm text-zinc-900 placeholder:text-zinc-400 focus:bg-white focus:border-zinc-900 focus:ring-4 focus:ring-zinc-900/5 outline-none transition-all duration-200" 
              placeholder="e.g. Molecular Biology Midterm"
              value={title} 
              onChange={e => setTitle(e.target.value)} 
              required
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-xs font-medium text-zinc-600 ml-1">Assessment Criteria</label>
              <button 
                type="button" 
                onClick={addCriterion} 
                className="inline-flex items-center gap-1 text-xs font-medium text-zinc-700 hover:text-black px-2.5 py-1 rounded-full glass-card-subtle hover:bg-white transition-colors"
              >
                <Plus size={14} className="stroke-[2]" />
                <span>Add Criterion</span>
              </button>
            </div>
            
            <div className="space-y-4">
              {criteria.map((c, i) => (
                <div key={i} className="p-5 rounded-2xl glass-card-subtle flex flex-col gap-4 relative group border border-black/[0.06]">
                  {criteria.length > 1 && (
                    <button 
                      type="button" 
                      onClick={() => removeCriterion(i)} 
                      className="absolute top-4 right-4 text-zinc-400 hover:text-rose-600 transition-colors p-1"
                      title="Remove criterion"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}

                  <div className="grid grid-cols-2 gap-4 mr-8">
                    <div>
                      <label className="block text-[11px] font-medium text-zinc-500 mb-1">Criterion ID</label>
                      <input 
                        type="text" 
                        className="w-full px-3 py-1.5 rounded-lg bg-white/80 border border-black/[0.08] text-xs text-zinc-900 font-mono focus:border-zinc-900 outline-none" 
                        value={c.id} 
                        onChange={e => updateCriterion(i, 'id', e.target.value)} 
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-zinc-500 mb-1">Weight</label>
                      <input 
                        type="number" 
                        step="0.1" 
                        className="w-full px-3 py-1.5 rounded-lg bg-white/80 border border-black/[0.08] text-xs text-zinc-900 focus:border-zinc-900 outline-none" 
                        value={c.weight} 
                        onChange={e => updateCriterion(i, 'weight', parseFloat(e.target.value) || 0)} 
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-zinc-500 mb-1">Description</label>
                    <textarea 
                      className="w-full px-3 py-2 rounded-lg bg-white/80 border border-black/[0.08] text-xs text-zinc-900 focus:border-zinc-900 outline-none h-16 resize-none" 
                      placeholder="Specify what claim or concept this criterion evaluates..."
                      value={c.description} 
                      onChange={e => updateCriterion(i, 'description', e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-zinc-500 mb-1">
                      Depends On (comma separated IDs)
                    </label>
                    <input 
                      type="text" 
                      className="w-full px-3 py-1.5 rounded-lg bg-white/80 border border-black/[0.08] text-xs text-zinc-900 font-mono focus:border-zinc-900 outline-none" 
                      placeholder="e.g. c1, c2"
                      value={c.depends_on.join(', ')} 
                      onChange={e => updateCriterion(i, 'depends_on', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} 
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <button 
              type="submit" 
              disabled={mutation.isPending} 
              className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl bg-zinc-900 hover:bg-black text-white text-sm font-medium tracking-tight shadow-sm hover:shadow transition-all duration-200 disabled:opacity-50 active:scale-[0.99]"
            >
              <span>{mutation.isPending ? 'Saving...' : 'Save Rubric'}</span>
              {!mutation.isPending && <ArrowRight className="w-4 h-4 stroke-[2]" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
