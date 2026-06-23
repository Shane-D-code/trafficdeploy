import { spawn } from 'child_process';
import path from 'path';

export class PythonBridge {
  private pythonPath: string;
  private modulePath: string;

  constructor() {
    const defaultPython = process.platform === 'win32' ? 'python' : 'python3';
    this.pythonPath = process.env.PYTHON_PATH || defaultPython;
    this.modulePath = path.resolve(__dirname, process.env.PYTHON_MODULE_PATH || '../../../traffic_violation_project');
    this._validatePaths();
  }

  private _validatePaths(): void {
    const pythonExists = (() => {
      try { require('child_process').execSync(`${this.pythonPath} --version`, { stdio: 'pipe' }); return true; }
      catch { return false; }
    })();
    if (!pythonExists) console.error(`[PythonBridge] Python binary not found at: ${this.pythonPath}. Set PYTHON_PATH in .env`);

    try {
      const fs = require('fs');
      if (!fs.existsSync(this.modulePath)) console.error(`[PythonBridge] Module path not found: ${this.modulePath}`);
    } catch {}
  }

  private _spawnPython(args: string[], mode: 'image' | 'video'): Promise<any> {
    return new Promise((resolve, reject) => {
      const script = path.join(this.modulePath, 'violation_detector.py');
      const fullArgs = [script, ...args];
      const timeoutMs = 300000;

      console.log(`[PythonBridge] Spawning: ${this.pythonPath} ${fullArgs.join(' ')}`);
      console.log(`[PythonBridge] CWD: ${this.modulePath}`);
      console.log(`[PythonBridge] Mode: ${mode}`);

      const proc = spawn(this.pythonPath, fullArgs, { cwd: this.modulePath });

      let stdout = '';
      let stderr = '';

      const timer = setTimeout(() => {
        console.error(`[PythonBridge] TIMEOUT after ${timeoutMs}ms for ${mode} job`);
        proc.kill('SIGTERM');
        reject(new Error(`Python ${mode} detection timed out after ${timeoutMs / 1000}s`));
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
          reject(new Error(`Python binary '${this.pythonPath}' not found. Check PYTHON_PATH in .env or install Python`));
        } else {
          reject(new Error(`Python spawn failed: ${err.message}`));
        }
      });

      proc.on('close', (code) => {
        clearTimeout(timer);
        console.log(`[PythonBridge] Process exited with code ${code}`);

        if (code !== 0) {
          const exitError = stderr.trim() || stdout.trim() || 'Unknown Python error (exit code ' + code + ')';
          console.error(`[PythonBridge] Non-zero exit: ${exitError}`);
          reject(new Error(`Python error (exit ${code}): ${exitError.slice(0, 500)}`));
          return;
        }

        if (!stdout.trim()) {
          console.error(`[PythonBridge] Empty stdout from Python`);
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
              resolve(json);
            }
          } else {
            console.error(`[PythonBridge] No JSON found in output. Raw stdout:\n${stdout.slice(0, 1000)}`);
            reject(new Error('No valid JSON found in Python output'));
          }
        } catch (error: any) {
          console.error(`[PythonBridge] JSON parse error: ${error.message}`);
          console.error(`[PythonBridge] Raw stdout (first 2000 chars):\n${stdout.slice(0, 2000)}`);
          if (stderr) console.error(`[PythonBridge] Raw stderr:\n${stderr}`);
          reject(new Error(`Failed to parse Python output: ${error.message}`));
        }
      });
    });
  }

  detectImage(imagePath: string, options: { confidenceThreshold: number; enablePreprocessing: boolean }): Promise<any> {
    const args = [
      '--image', imagePath,
      '--confidence', String(options.confidenceThreshold),
      '--preprocess', String(options.enablePreprocessing !== false),
      '--json'
    ];
    return this._spawnPython(args, 'image');
  }

  detectVideo(videoPath: string, options: { confidenceThreshold: number; frameInterval: number; maxFrames: number }): Promise<any> {
    const args = [
      '--video', videoPath,
      '--confidence', String(options.confidenceThreshold),
      '--interval', String(options.frameInterval),
      '--max-frames', String(options.maxFrames),
      '--json'
    ];
    return this._spawnPython(args, 'video');
  }

  private extractJSON(text: string): any {
    const trimmed = text.trim();
    try {
      return JSON.parse(trimmed);
    } catch (e1) {
      console.log(`[PythonBridge] Direct JSON parse failed, trying regex fallback...`);
    }
    try {
      const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[0]);
        } catch {}
      }
    } catch {}
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
    console.error(`[PythonBridge] All JSON parsing strategies failed for input (first 500 chars): ${trimmed.slice(0, 500)}`);
    return null;
  }
}
