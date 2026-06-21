import { spawn } from 'child_process';
import path from 'path';

export class PythonBridge {
  private pythonPath: string;
  private modulePath: string;

  constructor() {
    const defaultPython = process.platform === 'win32' ? 'python' : 'python3';
    this.pythonPath = process.env.PYTHON_PATH || defaultPython;
    this.modulePath = path.resolve(__dirname, process.env.PYTHON_MODULE_PATH || '../../../traffic_violation_project');
  }

  detectImage(imagePath: string, options: { confidenceThreshold: number; enablePreprocessing: boolean }): Promise<any> {
    return new Promise((resolve, reject) => {
      const script = path.join(this.modulePath, 'violation_detector.py');
      const args = [
        script, '--image', imagePath,
        '--confidence', String(options.confidenceThreshold),
        '--preprocess', String(options.enablePreprocessing !== false),
        '--json'
      ];

      console.log('Running Python:', args.join(' '));

      const proc = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => { stdout += data.toString(); });
      proc.stderr.on('data', (data) => {
        const chunk = data.toString();
        stderr += chunk;
        console.log('Python log:', chunk.trim());
      });

      proc.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);

        if (code !== 0) {
          reject(new Error(`Python error: ${stderr || stdout}`));
          return;
        }

        try {
          const json = this.extractJSON(stdout);
          if (json) {
            resolve(json);
          } else {
            reject(new Error('No valid JSON found in Python output'));
          }
        } catch (error: any) {
          console.error('Failed to parse Python output:', stdout);
          reject(new Error(`Failed to parse Python output: ${error.message}`));
        }
      });

      proc.on('error', reject);
    });
  }

  detectVideo(videoPath: string, options: { confidenceThreshold: number; frameInterval: number; maxFrames: number }): Promise<any> {
    return new Promise((resolve, reject) => {
      const script = path.join(this.modulePath, 'violation_detector.py');
      const args = [
        script, '--video', videoPath,
        '--confidence', String(options.confidenceThreshold),
        '--interval', String(options.frameInterval),
        '--max-frames', String(options.maxFrames),
        '--json'
      ];

      console.log('Running Python video:', args.join(' '));

      const proc = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => { stdout += data.toString(); });
      proc.stderr.on('data', (data) => {
        const chunk = data.toString();
        stderr += chunk;
        console.log('Python log:', chunk.trim());
      });

      proc.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Python error: ${stderr || stdout}`));
          return;
        }

        try {
          const json = this.extractJSON(stdout);
          if (json) {
            resolve(json);
          } else {
            reject(new Error('No valid JSON found in Python output'));
          }
        } catch (error: any) {
          console.error('Failed to parse Python output:', stdout);
          reject(new Error(`Failed to parse Python output: ${error.message}`));
        }
      });

      proc.on('error', reject);
    });
  }

  private extractJSON(text: string): any {
    const trimmed = text.trim();
    try {
      return JSON.parse(trimmed);
    } catch {
      const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[0]);
        } catch {}
      }
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
      return null;
    }
  }
}
