import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile, mkdir, rm } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { randomUUID } from 'crypto';
import os from 'os';

const execFileAsync = promisify(execFile);
const JUDGE = 'C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\Default Project\\local-qc\\scripts\\judge_v2.py';

export const runtime = 'nodejs';
export const maxDuration = 180;

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('zip') as File;
    const useModel = formData.get('model') === 'true';

    if (!file) {
      return NextResponse.json({ error: 'No zip file uploaded' }, { status: 400 });
    }

    const tmpDir = join(os.tmpdir(), `qc-upload-${randomUUID()}`);
    await mkdir(tmpDir, { recursive: true });
    const zipPath = join(tmpDir, file.name);
    const bytes = await file.arrayBuffer();
    await writeFile(zipPath, Buffer.from(bytes));

    const args = [JUDGE, zipPath];
    if (!useModel) {
      args.push('--no-model');
    }

    let stdout = '';
    let stderr = '';
    try {
      const result = await execFileAsync('python', args, {
        timeout: 180000,
        env: { ...process.env, PYTHONUTF8: '1', NO_COLOR: '1' },
        maxBuffer: 20 * 1024 * 1024,
        windowsHide: true,
      });
      stdout = result.stdout;
      stderr = result.stderr;
    } catch (err: any) {
      // judge.py exits 1 for FAIL/NEEDS_REVIEW — that's a valid result, not a crash
      if (err.stdout) {
        stdout = err.stdout;
        stderr = err.stderr || '';
      } else {
        throw err;
      }
    }

    // Parse stdout into structured findings for the UI
    const findings = parseFindings(stdout);
    const verdict = parseVerdict(stdout);
    const counts = parseCounts(stdout);
    const components = parseComponents(stdout);
    const gates = parseGates(stdout);
    const rewardHacking = parseRewardHacking(stdout);

    // Also try to read the judge-report.json
    let reportJson = null;
    const reportMatch = (stdout.match(/C:\\[^\s]+judge-report\.json/) || [])[0];
    if (reportMatch && existsSync(reportMatch)) {
      try {
        reportJson = JSON.parse(await readFile(reportMatch, 'utf-8'));
      } catch {
        // ignore parse errors
      }
    }

    await rm(tmpDir, { recursive: true, force: true }).catch(() => {});

    return NextResponse.json({
      stdout: stdout.slice(-12000),
      stderr: stderr.slice(-2000),
      report: reportJson,
      parsed: {
        verdict,
        counts,
        findings,
        components,
        gates,
        rewardHacking,
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

function parseVerdict(stdout: string): string {
  const m = stdout.match(/VERDICT:\s*(\w+)/);
  return m ? m[1] : 'UNKNOWN';
}

function parseCounts(stdout: string): Record<string, number> {
  const m = stdout.match(/P0:\s*(\d+)\s+P1:\s*(\d+)\s+P2:\s*(\d+)\s+INFO:\s*(\d+)/);
  if (m) {
    return {
      P0: parseInt(m[1]),
      P1: parseInt(m[2]),
      P2: parseInt(m[3]),
      INFO: parseInt(m[4]),
    };
  }
  return { P0: 0, P1: 0, P2: 0, INFO: 0 };
}

function parseFindings(stdout: string): Array<{
  severity: string;
  id: string;
  label: string;
  title: string;
  where: string;
  fact: string;
  impact: string;
  fix: string;
}> {
  const findings: Array<{
    severity: string;
    id: string;
    label: string;
    title: string;
    where: string;
    fact: string;
    impact: string;
    fix: string;
  }> = [];

  // Match finding blocks: [P0] [ID] (label) title\n    where : ...\n    fact : ...\n    impact: ...\n    fix : ...
  const blocks = stdout.split(/\n(?=\[(?:P0|P1|P2|INFO)\])/);
  for (const block of blocks) {
    const sevMatch = block.match(/^\[(P0|P1|P2|INFO)\]/);
    if (!sevMatch) continue;
    const severity = sevMatch[1];

    const idMatch = block.match(/\[([^\]]+)\]\s*\(([^)]+)\)/);
    const id = idMatch ? idMatch[1] : '';
    const label = idMatch ? idMatch[2] : '';

    const titleMatch = block.match(/\)\s*(.+)/);
    const title = titleMatch ? titleMatch[1].trim() : '';

    const whereMatch = block.match(/where\s*:\s*(.+)/);
    const where = whereMatch ? whereMatch[1].trim() : '';

    const factMatch = block.match(/fact\s*:\s*(.+)/);
    const fact = factMatch ? factMatch[1].trim() : '';

    const impactMatch = block.match(/impact\s*:\s*(.+)/);
    const impact = impactMatch ? impactMatch[1].trim() : '';

    const fixMatch = block.match(/fix\s*:\s*(.+)/);
    const fix = fixMatch ? fixMatch[1].trim() : '';

    if (title) {
      findings.push({ severity, id, label, title, where, fact, impact, fix });
    }
  }
  return findings;
}

function parseComponents(stdout: string): Record<string, string> {
  const components: Record<string, string> = {};
  const lines = stdout.split('\n');
  let inComponents = false;
  for (const line of lines) {
    if (line.includes('Component verdicts:')) {
      inComponents = true;
      continue;
    }
    if (line.includes('======')) {
      if (inComponents) break;
      continue;
    }
    if (inComponents && line.includes(':')) {
      const [key, val] = line.split(':').map((s) => s.trim());
      if (key && val) {
        components[key] = val;
      }
    }
  }
  return components;
}

function parseGates(stdout: string): Record<string, string> {
  const gates: Record<string, string> = {};
  const lines = stdout.split('\n');
  for (const line of lines) {
    const m = line.match(/gate\s+(\w+)\s+(\w+)/);
    if (m) {
      gates[m[1]] = m[2];
    }
  }
  return gates;
}

function parseRewardHacking(stdout: string): string {
  const m = stdout.match(/reward_hacking\s*:\s*(\w+)/);
  return m ? m[1] : 'OK';
}
