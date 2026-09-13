#!/usr/bin/env node
/**
 * Opt-in build pipeline for static/js/.
 *
 * Templates currently include each file in static/js/ individually via its
 * own <script src="{% static 'js/<name>.js' %}"> tag (see templates/base.html,
 * templates/core/landing.html, templates/explore/place_detail.html, etc.).
 * There is no bundler wiring those tags together, so this script preserves
 * that layout: every top-level file in static/js/ (and static/js/components/)
 * is built as its own minified, standalone entry point under static/js/dist/,
 * mirroring the source path. Nothing currently points <script src> at
 * static/js/dist/ - this is opt-in tooling, not a template change.
 */
import { build } from 'esbuild';
import { globSync } from 'fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const srcDir = path.join(rootDir, 'static', 'js');
const outDir = path.join(srcDir, 'dist');

const entryPoints = globSync('**/*.js', { cwd: srcDir })
  .filter(file => !file.startsWith('dist' + path.sep) && !file.startsWith('dist/'))
  .map(file => path.join(srcDir, file));

if (entryPoints.length === 0) {
  console.error('No JS entry points found under static/js/.');
  process.exit(1);
}

await build({
  entryPoints,
  outbase: srcDir,
  outdir: outDir,
  bundle: false,
  minify: true,
  sourcemap: true,
  target: ['es2021'],
  format: 'iife',
  logLevel: 'info',
});

console.log(
  `Built ${entryPoints.length} JS entry point(s) to ${path.relative(rootDir, outDir)}/`
);
