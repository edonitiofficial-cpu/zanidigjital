function adminDisplayRecord(record) {
    return Object.fromEntries(Object.entries(record).map(([key, value]) => {
        if (key === 'id') {
            if (!/^[a-zA-Z0-9_-]+$/.test(String(value))) throw new Error('ID e pavlefshme.');
            return [key, value];
        }
        if (typeof value !== 'string') return [key, value];
        if (key.endsWith('_url') || key.endsWith('_link')) return [key, escapeHTML(safeURL(value))];
        return [key, escapeHTML(value)];
    }));
}

async function adminRequest(query) {
    const result = await query;
    if (result.error) throw new Error(result.error.message || 'Veprimi dështoi.');
    return result;
}

function kosovoInputToISO(value) {
    if (!value) return new Date().toISOString();
    const instant = kosovoCivilTimestamp(value);
    if (Number.isFinite(instant)) return new Date(instant).toISOString();
    throw new Error('Kjo orë nuk ekziston për shkak të kalimit verë/dimër. Zgjedh një orë tjetër.');
}
