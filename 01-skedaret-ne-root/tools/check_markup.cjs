/* Use the same CSS parser as VS Code; also compile inline JavaScript. */
const fs = require('node:fs');
const vm = require('node:vm');
const { getCSSLanguageService } = require('vscode-css-languageservice');
const { TextDocument } = require('vscode-languageserver-textdocument');
const css = getCSSLanguageService();
let errors = 0;
for (const file of process.argv.slice(2).length ? process.argv.slice(2) : ['index.html']) {
    const html = fs.readFileSync(file, 'utf8');
    for (const match of html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)) {
        const doc = TextDocument.create('file:///' + file + '.css', 'css', 1, match[1]);
        for (const diagnostic of css.doValidation(doc, css.parseStylesheet(doc)).filter(d => d.severity === 1)) {
            errors++;
            const line = html.slice(0, match.index).split('\n').length + diagnostic.range.start.line;
            console.error(`${file}:${line}: ${diagnostic.message}`);
        }
    }
    for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
        if (/\bsrc\s*=|application\/ld\+json/i.test(match[1]) || !match[2].trim()) continue;
        try { new vm.Script(match[2], { filename: file }); }
        catch (error) { errors++; console.error(error.message); }
    }
}
console.log(`CSS / inline JavaScript errors: ${errors}`);
process.exitCode = errors ? 1 : 0;
