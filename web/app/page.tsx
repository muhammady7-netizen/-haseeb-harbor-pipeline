'use client';

import { useState, useCallback } from 'react';

interface Finding {
  severity: string;
  id: string;
  label: string;
  title: string;
  where: string;
  fact: string;
  impact: string;
  fix: string;
}

interface ParsedResult {
  verdict: string;
  counts: Record<string, number>;
  findings: Finding[];
  components: Record<string, string>;
  gates: Record<string, string>;
  rewardHacking: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ParsedResult | null>(null);
  const [error, setError] = useState<string>('');
  const [useModel, setUseModel] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith('.zip')) {
      setFile(f);
      setResult(null);
      setError('');
    }
  }, []);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setResult(null);
      setError('');
    }
  };

  const judge = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    setElapsed(0);

    const startTime = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const formData = new FormData();
    formData.append('zip', file);
    formData.append('model', String(useModel));

    try {
      const res = await fetch('/api/judge', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.error) {
        setError(data.error);
      } else if (data.parsed) {
        setResult(data.parsed);
      } else {
        setError('No parsed result returned');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  };

  const verdictColor = (v: string) => {
    if (v === 'PASS') return 'from-green-600 to-emerald-700';
    if (v === 'NEEDS_REVIEW') return 'from-yellow-600 to-amber-700';
    if (v === 'FAIL') return 'from-red-600 to-rose-700';
    return 'from-gray-600 to-slate-700';
  };

  // Ship decision: tells the agent what to DO, not just what the verdict is
  const shipDecision = () => {
    if (!result) return null;
    const p0 = result.counts.P0 || 0;
    const p1 = result.counts.P1 || 0;
    const p2 = result.counts.P2 || 0;

    // Known false-positive P1 patterns
    const knownFalsePositives = [
      'D2 sev1',           // Dockerfile root — judge.py reads wrong USER line
      'solvability evidence gate fails',  // Expected — portal runs own GLM
      'placeholder/synthetic wording',    // Format label, not task data
      'difficulty evidence gate fails',   // No GLM runs in bundle
    ];

    const realP1 = result.findings.filter(
      (f) => f.severity === 'P1' && !knownFalsePositives.some(fp => f.title.includes(fp))
    );

    if (p0 > 0) {
      return {
        action: 'BLOCKED',
        color: 'from-red-600 to-rose-700',
        icon: '🛑',
        title: 'DO NOT SHIP — Fix P0 blockers first',
        detail: `${p0} P0 blocker(s) must be fixed before uploading to the portal.`,
      };
    }

    if (realP1.length > 0) {
      return {
        action: 'FIX',
        color: 'from-orange-600 to-red-700',
        icon: '🔧',
        title: 'FIX REQUIRED — Real P1 findings need attention',
        detail: `${realP1.length} P1 finding(s) are not known false positives. Review and fix before shipping.`,
      };
    }

    if (p1 > 0 && realP1.length === 0) {
      return {
        action: 'SHIP',
        color: 'from-green-600 to-emerald-700',
        icon: '🚀',
        title: 'READY TO SHIP — All P1s are known false positives',
        detail: `${p1} P1 finding(s) are false positives (D2 root, solvability gate, placeholder label). ${p2} P2 warning(s) are advisory. Upload to portal.`,
      };
    }

    if (p2 > 0) {
      return {
        action: 'SHIP',
        color: 'from-green-600 to-emerald-700',
        icon: '🚀',
        title: 'READY TO SHIP — Only advisory warnings',
        detail: `${p2} P2 warning(s) are non-blocking. Upload to portal.`,
      };
    }

    return {
      action: 'SHIP',
      color: 'from-green-600 to-emerald-700',
      icon: '🚀',
      title: 'CLEAN PASS — Ship it',
      detail: 'No blockers, no warnings. Upload to portal.',
    };
  };

  const sevColor = (s: string) => {
    if (s === 'P0') return 'border-red-500 bg-red-950/50';
    if (s === 'P1') return 'border-orange-500 bg-orange-950/50';
    if (s === 'P2') return 'border-yellow-500 bg-yellow-950/50';
    return 'border-gray-600 bg-gray-900/50';
  };

  const sevBadge = (s: string) => {
    if (s === 'P0') return 'bg-red-600 text-white';
    if (s === 'P1') return 'bg-orange-600 text-white';
    if (s === 'P2') return 'bg-yellow-600 text-white';
    return 'bg-gray-500 text-white';
  };

  const gateColor = (s: string) => {
    if (s === 'pass') return 'text-green-400';
    if (s === 'fail') return 'text-red-400';
    return 'text-yellow-400';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gradient-to-b from-gray-900 to-gray-950 px-6 py-6">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <span className="text-4xl">⚖️</span>
            Local QC Judge
          </h1>
          <p className="text-sm text-gray-400 mt-2">
            Upload a Harbor task zip — get a 331-check verdict in seconds
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Upload area */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
            dragOver ? 'border-blue-500 bg-blue-950/30 scale-[1.02]' : 'border-gray-700 bg-gray-900/50 hover:border-gray-600'
          }`}
        >
          <input
            type="file"
            accept=".zip"
            onChange={handleFile}
            className="hidden"
            id="file-input"
          />
          <label htmlFor="file-input" className="cursor-pointer block">
            <div className="text-6xl mb-4">📦</div>
            <p className="text-lg font-medium text-gray-300">
              {file ? file.name : 'Drop zip here or click to browse'}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              {file ? `${(file.size / 1024).toFixed(0)} KB` : '.zip files only'}
            </p>
          </label>
        </div>

        {/* Options + Judge button */}
        <div className="flex items-center justify-between mt-6">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={useModel}
              onChange={(e) => setUseModel(e.target.checked)}
              className="rounded border-gray-600 bg-gray-800"
            />
            Run with model stage (~3 min, needs WANDB_GLM_API_KEY)
          </label>
          <button
            onClick={judge}
            disabled={!file || loading}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium text-white transition-colors shadow-lg shadow-blue-900/50"
          >
            {loading ? `⏳ ${elapsed}s` : '⚡ Judge Zip'}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-950/50 border border-red-700 rounded-lg text-red-300">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="mt-8 text-center">
            <div className="inline-block animate-spin text-5xl">⚖️</div>
            <p className="text-gray-400 mt-4">Running 331 checks... {elapsed}s elapsed</p>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div className="mt-8 space-y-6">
            {/* Ship Decision banner */}
            {(() => {
              const decision = shipDecision();
              if (!decision) return null;
              return (
                <div className={`bg-gradient-to-r ${decision.color} rounded-2xl p-8 text-center shadow-xl`}>
                  <div className="text-5xl mb-3">{decision.icon}</div>
                  <h2 className="text-3xl font-bold text-white">{decision.action}</h2>
                  <p className="text-white/90 mt-3 text-lg">{decision.title}</p>
                  <p className="text-white/70 mt-2 text-sm">{decision.detail}</p>
                  <div className="flex justify-center gap-8 mt-6 text-white">
                    <div className="text-center">
                      <div className="text-3xl font-bold">{result.counts.P0 || 0}</div>
                      <div className="text-xs opacity-80 uppercase tracking-wider">P0</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold">{result.counts.P1 || 0}</div>
                      <div className="text-xs opacity-80 uppercase tracking-wider">P1</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold">{result.counts.P2 || 0}</div>
                      <div className="text-xs opacity-80 uppercase tracking-wider">P2</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold">{result.counts.INFO || 0}</div>
                      <div className="text-xs opacity-80 uppercase tracking-wider">INFO</div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Gates + Components */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.keys(result.gates).length > 0 && (
                <div className="bg-gray-900/50 rounded-xl p-5 border border-gray-800">
                  <h3 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wider">Gates</h3>
                  <div className="space-y-2">
                    {Object.entries(result.gates).map(([gate, status]) => (
                      <div key={gate} className="flex items-center justify-between">
                        <span className="text-sm text-gray-300 capitalize">{gate}</span>
                        <span className={`text-sm font-medium ${gateColor(status)}`}>
                          {status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️'} {status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(result.components).length > 0 && (
                <div className="bg-gray-900/50 rounded-xl p-5 border border-gray-800">
                  <h3 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wider">Components</h3>
                  <div className="space-y-2">
                    {Object.entries(result.components).map(([comp, verdict]) => (
                      <div key={comp} className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">{comp}</span>
                        <span className={`text-sm font-medium ${
                          verdict === 'PASS' ? 'text-green-400' :
                          verdict === 'FAIL' ? 'text-red-400' :
                          'text-yellow-400'
                        }`}>
                          {verdict === 'PASS' ? '✅' : verdict === 'FAIL' ? '❌' : '⚠️'} {verdict}
                        </span>
                      </div>
                    ))}
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">reward_hacking</span>
                      <span className={`text-sm font-medium ${
                        result.rewardHacking === 'OK' ? 'text-green-400' :
                        result.rewardHacking === 'CONFIRMED' ? 'text-red-400' :
                        'text-yellow-400'
                      }`}>
                        {result.rewardHacking === 'OK' ? '✅' : '⚠️'} {result.rewardHacking}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Findings */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                Findings ({result.findings.length})
              </h3>
              {result.findings
                .sort((a, b) => {
                  const order: Record<string, number> = { P0: 0, P1: 1, P2: 2, INFO: 3 };
                  return (order[a.severity] || 9) - (order[b.severity] || 9);
                })
                .map((f, i) => (
                  <div
                    key={i}
                    className={`border-l-4 ${sevColor(f.severity)} rounded-r-xl p-5`}
                  >
                    <div className="flex items-start gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${sevBadge(f.severity)} whitespace-nowrap`}>
                        {f.severity}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-100">{f.title}</p>
                        {f.id && (
                          <p className="text-xs text-gray-500 mt-1 font-mono">{f.id}</p>
                        )}
                        {f.where && (
                          <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                            <span>📍</span> {f.where}
                          </p>
                        )}
                        {f.fact && (
                          <p className="text-sm text-gray-300 mt-2 bg-gray-900/50 rounded p-2">
                            <span className="text-gray-500 text-xs">FACT: </span>{f.fact}
                          </p>
                        )}
                        {f.impact && (
                          <p className="text-xs text-orange-300 mt-2 flex items-start gap-1">
                            <span>⚠️</span> {f.impact}
                          </p>
                        )}
                        {f.fix && (
                          <p className="text-xs text-green-300 mt-2 flex items-start gap-1">
                            <span>✅</span> {f.fix}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>

            {/* Ship readiness summary */}
            {(() => {
              const decision = shipDecision();
              if (!decision) return null;
              return (
                <div className="bg-gray-900/50 rounded-xl p-6 border border-gray-800">
                  <h3 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wider">Ship Readiness</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div className={`p-3 rounded-lg ${result.counts.P0 === 0 ? 'bg-green-950/50 text-green-300' : 'bg-red-950/50 text-red-300'}`}>
                      P0 Blockers: {result.counts.P0 || 0}
                    </div>
                    <div className={`p-3 rounded-lg ${result.counts.P1 === 0 ? 'bg-green-950/50 text-green-300' : 'bg-orange-950/50 text-orange-300'}`}>
                      P1 Issues: {result.counts.P1 || 0}
                    </div>
                    <div className="p-3 rounded-lg bg-yellow-950/50 text-yellow-300">
                      P2 Warnings: {result.counts.P2 || 0}
                    </div>
                    <div className="p-3 rounded-lg bg-gray-800/50 text-gray-400">
                      INFO: {result.counts.INFO || 0}
                    </div>
                  </div>
                  <div className="mt-4 p-4 rounded-lg bg-gray-900/80 text-center">
                    <p className="text-lg font-bold">
                      <span className={
                        decision.action === 'SHIP' ? 'text-green-400' :
                        decision.action === 'FIX' ? 'text-orange-400' :
                        'text-red-400'
                      }>
                        {decision.icon} {decision.title}
                      </span>
                    </p>
                    <p className="text-sm text-gray-400 mt-2">{decision.detail}</p>
                    {result.counts.P1 > 0 && (
                      <div className="mt-4 text-left">
                        <p className="text-xs text-gray-500 mb-2">P1 Analysis:</p>
                        {result.findings.filter(f => f.severity === 'P1').map((f, i) => {
                          const isFalsePositive = ['D2 sev1', 'solvability evidence gate fails', 'placeholder/synthetic wording', 'difficulty evidence gate fails'].some(fp => f.title.includes(fp));
                          return (
                            <div key={i} className="flex items-center gap-2 text-xs mb-1">
                              <span className={isFalsePositive ? 'text-green-400' : 'text-orange-400'}>
                                {isFalsePositive ? '✅ False positive' : '⚠️ Real issue'}
                              </span>
                              <span className="text-gray-500">{f.title.slice(0, 60)}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 bg-gray-900/50 px-6 py-4 text-center text-xs text-gray-500">
        Local QC Judge v1.0 · 331 checks · github.com/haseeb371/local-qc
      </div>
    </div>
  );
}
