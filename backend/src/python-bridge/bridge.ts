import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { EventEmitter } from 'events';

export class PythonBridge extends EventEmitter {
  private pythonPath: string;
  private modulePath: string;

  constructor() {
    super();
    this.pythonPath = this.findPythonPath();
    this.modulePath = this.findModulePath();

    console.log(`[PythonBridge] Python: ${this.pythonPath}`);
    console.log(`[PythonBridge] Module: ${this.modulePath}`);

    if (!fs.existsSync(this.modulePath)) {
      throw new Error(`Python module path not found: ${this.modulePath}`);
    }
  }

  private findPythonPath(): string {
    const paths = [
      process.env.PYTHON_PATH,
      '/Users/shantanu/Gridlock/traffic_violation_project/venv/bin/python3',
      '/usr/bin/python3',
      '/opt/homebrew/bin/python3',
      'python3',
      'python'
    ];
    for (const p of paths) {
      if (p && (p === 'python3' || p === 'python' || fs.existsSync(p))) {
        // For bare names, check they're on PATH
        if (p === 'python3' || p === 'python') {
          try {
            require('child_process').execSync(`${p} --version`, { stdio: 'pipe' });
            return p;
          } catch { continue; }
        }
        return p;
      }
    }
    return 'python3';
  }

  private findModulePath(): string {
    const paths = [
      process.env.PYTHON_MODULE_PATH,
      path.resolve(__dirname, '../../../traffic_violation_project'),
      path.resolve(__dirname, '../../../../traffic_violation_project'),
      path.join(process.cwd(), 'traffic_violation_project')
    ];
    for (const p of paths) {
      if (p && fs.existsSync(p)) {
        return p;
      }
    }
    throw new Error('Could not find traffic_violation_project directory');
  }

  detectImage(imagePath: string, options: { confidenceThreshold: number; enablePreprocessing: boolean; useEnhancedModels?: boolean }): Promise<any> {
    const args = [
      '--image', imagePath,
      '--confidence', String(options.confidenceThreshold),
      '--preprocess', String(options.enablePreprocessing !== false),
      '--json'
    ];
    if (options.useEnhancedModels) args.push('--enhanced');
    return this.runPython(args);
  }

  detectVideo(videoPath: string, options: { confidenceThreshold: number; frameInterval: number; maxFrames: number; useEnhancedModels?: boolean }): Promise<any> {
    const args = [
      '--video', videoPath,
      '--confidence', String(options.confidenceThreshold),
      '--interval', String(options.frameInterval),
      '--max-frames', String(options.maxFrames),
      '--json'
    ];
    if (options.useEnhancedModels) args.push('--enhanced');
    return this.runPython(args);
  }

  private async runPython(args: string[]): Promise<any> {
    return new Promise((resolve, reject) => {
      const script = path.join(this.modulePath, 'violation_detector.py');
      const fullArgs = [script, ...args];
      const timeoutMs = 300000;

      console.log(`[PythonBridge] Spawning: ${this.pythonPath} ${fullArgs.join(' ')}`);
      console.log(`[PythonBridge] CWD: ${this.modulePath}`);

      const proc = spawn(this.pythonPath, fullArgs, {
        cwd: this.modulePath,
        env: { ...process.env, PYTHONPATH: this.modulePath }
      });

      let stdout = '';
      let stderr = '';

      const timer = setTimeout(() => {
        console.error(`[PythonBridge] TIMEOUT after ${timeoutMs}ms`);
        proc.kill('SIGTERM');
        reject(new Error(`Python detection timed out after ${timeoutMs / 1000}s`));
      }, timeoutMs);

      proc.stdout.on('data', (data: Buffer) => {
        const chunk = data.toString();
        stdout += chunk;
        console.log(`[PythonBridge:stdout] ${chunk.trim()}`);
      });

      proc.stderr.on('data', (data: Buffer) => {
        const chunk = data.toString();
        stderr += chunk;
        console.log(`[PythonBridge:stderr] ${chunk.trim()}`);
      });

      proc.on('error', (err) => {
        clearTimeout(timer);
        console.error(`[PythonBridge] Spawn error: ${err.message}`);
        if (err.message.includes('ENOENT')) {
          reject(new Error(`Python binary '${this.pythonPath}' not found. Check PYTHON_PATH or install Python`));
        } else {
          reject(new Error(`Python spawn failed: ${err.message}`));
        }
      });

      proc.on('close', (code) => {
        clearTimeout(timer);
        console.log(`[PythonBridge] Process exited with code ${code}`);

        if (code !== 0) {
          const exitError = stderr.trim() || stdout.trim() || `Unknown Python error (exit code ${code})`;
          console.error(`[PythonBridge] Non-zero exit: ${exitError}`);
          this.emit('error', { code, stderr, stdout });
          reject(new Error(`Python error (exit ${code}): ${exitError.slice(0, 500)}`));
          return;
        }

        if (!stdout.trim()) {
          console.error(`[PythonBridge] Empty stdout`);
          reject(new Error('Python produced no output'));
          return;
        }

        try {
          const json = this.extractJSON(stdout);
          if (json) {
            if (json.error) {
              console.error(`[PythonBridge] Python returned error: ${json.error}`);
              reject(new Error(`Python detection error: ${json.error}`));
            } else {
              this.emit('result', json);
              resolve(json);
            }
          } else {
            const snippet = stdout.slice(0, 1000);
            console.error(`[PythonBridge] No JSON found:\n${snippet}`);
            reject(new Error('No valid JSON found in Python output'));
          }
        } catch (error: any) {
          console.error(`[PythonBridge] Parse error: ${error.message}`);
          console.error(`[PythonBridge] stdout:\n${stdout.slice(0, 2000)}`);
          if (stderr) console.error(`[PythonBridge] stderr:\n${stderr}`);
          reject(new Error(`Failed to parse Python output: ${error.message}`));
        }
      });
    });
  }

  private extractJSON(text: string): any {
    const trimmed = text.trim();
    // Try direct parse
    try {
      return JSON.parse(trimmed);
    } catch {}
    // Try regex extraction
    try {
      const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try { return JSON.parse(jsonMatch[0]); } catch {}
      }
    } catch {}
    // Try brace-matching extraction
    let inString = false;
    let escape = false;
    let braceCount = 0;
    let start = -1;
    let end = -1;
    for (let i = 0; i < trimmed.length; i++) {
      const char = trimmed[i];
      if (escape) { escape = false; continue; }
      if (char === '\\') { escape = true; continue; }
      if (char === '"') { inString = !inString; continue; }
      if (!inString) {
        if (char === '{') {
          if (braceCount === 0) start = i;
          braceCount++;
        } else if (char === '}') {
          braceCount--;
          if (braceCount === 0) { end = i; break; }
        }
      }
    }
    if (start !== -1 && end !== -1) {
      try { return JSON.parse(trimmed.substring(start, end + 1)); } catch {}
    }
    console.error(`[PythonBridge] All JSON parsing strategies failed (first 500 chars): ${trimmed.slice(0, 500)}`);
    return null;
  }
}
