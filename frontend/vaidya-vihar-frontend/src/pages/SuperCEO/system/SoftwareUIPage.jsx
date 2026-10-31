import { useEffect, useMemo, useRef, useState } from 'react';
import { themeApi } from '../../../services/themeApi';
import { useTokenEditor } from '../../../hooks/useTokenEditor';
import '../../../styles/software-ui.css';

const FALLBACK_TOKENS = {
  color: { semantic: { primary: '#8B5E17', secondary: '#8C78F5', accent: '#57C7F2', success: '#56C58A', warning: '#E8A24A', danger: '#E87986' }, surface: { default: '#090B14', panel: '#25293D', elevated: '#2B2F45' }, text: { primary: '#FFF9EC', secondary: '#D2CFD8', tertiary: '#B7B5C1', muted: '#9698A8' }, border: { default: '#4B4D5A', focus: '#F3D58A' } },
  typography: { family: { display: 'Fraunces', body: 'Manrope' }, size: { base: '16px', sm: '12px', lg: '20px' }, weight: { regular: 400, semibold: 600 }, line_height: { base: 1.5 }, letter_spacing: { base: '0px' } },
  spacing: { scale: [0, 4, 8, 12, 16, 24, 32], padding: { sm: '8px', md: '16px', lg: '24px' }, margin: { sm: '8px', md: '16px', lg: '24px' }, gap: { sm: '8px', md: '16px', lg: '24px' } },
  radius: { none: '0px', sm: '8px', md: '12px', lg: '20px', xl: '28px', pill: '999px' },
  shadow: { elevation_1: '0 2px 8px rgba(0,0,0,.18)', elevation_2: '0 8px 20px rgba(0,0,0,.22)' },
  gradient: { families: {} }, motion: { duration: { fast: '120ms', normal: '220ms', slow: '400ms' }, easing: { standard: 'ease', emphasized: 'ease-in-out' } }, icon: { size: 24, stroke: 1.5 },
};

const merge = (base, value) => Object.keys(base).reduce((result, key) => ({ ...result, [key]: value?.[key] && typeof value[key] === 'object' && !Array.isArray(value[key]) ? merge(base[key], value[key]) : value?.[key] ?? base[key] }), {});
const colorPaths = ['color.semantic.primary', 'color.semantic.secondary', 'color.semantic.accent', 'color.semantic.success', 'color.semantic.warning', 'color.semantic.danger', 'color.surface.default', 'color.surface.panel', 'color.surface.elevated', 'color.text.primary', 'color.text.secondary', 'color.text.tertiary', 'color.text.muted', 'color.border.default', 'color.border.focus'];
const categoryLabels = ['Colors', 'Typography', 'Spacing', 'Radius', 'Shadow', 'Gradient', 'Motion', 'Icons'];
const pathValue = (tokens, path) => path.split('.').reduce((value, key) => value?.[key], tokens);

function ProfileRail({ profiles, selected, onSelect, search, onSearch }) {
  const filtered = profiles.filter((profile) => `${profile.display_name} ${profile.key}`.toLowerCase().includes(search.toLowerCase()));
  return <aside className="software-ui-rail">
    <input className="software-ui-search" value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search profile types…" aria-label="Search profile types" />
    <h3>System profile types</h3>
    {filtered.filter((profile) => profile.is_system).map((profile) => <button type="button" className={`profile-type-item ${selected?.id === profile.id ? 'selected' : ''}`} key={profile.id} onClick={() => onSelect(profile)}><span className="exec-icon-badge exec-icon-badge-gold exec-icon-badge-medium">✦</span><span className="profile-type-copy"><strong>{profile.display_name}</strong><small>system · {profile.key}</small></span>{selected?.id === profile.id && <i className="profile-type-dot" />}</button>)}
    {filtered.some((profile) => !profile.is_system) && <h3>Custom profile types</h3>}
    {filtered.filter((profile) => !profile.is_system).map((profile) => <button type="button" className={`profile-type-item ${selected?.id === profile.id ? 'selected' : ''}`} key={profile.id} onClick={() => onSelect(profile)}><span className="exec-icon-badge exec-icon-badge-violet exec-icon-badge-medium">◇</span><span className="profile-type-copy"><strong>{profile.display_name}</strong><small>custom · {profile.key}</small></span></button>)}
  </aside>;
}

function ColorEditor({ tokens, updateToken, reset }) {
  return <><div className="editor-subtitle">Color tokens</div>{colorPaths.map((path) => {
    const value = pathValue(tokens, path) || '#000000';
    return <div className="token-row" key={path}><label htmlFor={`token-${path}`}>{path}</label><input type="color" value={value.startsWith('#') ? value : '#000000'} onChange={(event) => updateToken(path, event.target.value)} aria-label={`${path} color`} /><input id={`token-${path}`} value={value} onChange={(event) => updateToken(path, event.target.value)} /><button type="button" onClick={() => reset(path)} aria-label={`Reset ${path}`}>↺</button></div>;
  })}</>;
}

function GenericEditor({ category, tokens, updateToken }) {
  const values = tokens[category] || {};
  const entries = Object.entries(values).flatMap(([group, value]) => typeof value === 'object' && !Array.isArray(value) ? Object.entries(value).map(([key, nested]) => [`${category}.${group}.${key}`, nested]) : [[`${category}.${group}`, value]]);
  return <><div className="editor-subtitle">{category} tokens</div>{entries.map(([path, value]) => <div className="token-row" key={path}><label htmlFor={`token-${path}`}>{path}</label><span /><input id={`token-${path}`} value={Array.isArray(value) ? value.join(', ') : value ?? ''} onChange={(event) => updateToken(path, event.target.value)} /><span /></div>)}</>;
}

function AccessibilityPanel({ report }) {
  const failures = report?.failures || [];
  return <section className="accessibility-panel" aria-live="polite"><h3>Accessibility checker</h3><div className={`accessibility-summary ${failures.length ? 'status-fail' : 'status-pass'}`}>{failures.length ? '⚠ Contrast needs attention' : '✓ WCAG AA contrast passing'}</div>{(report?.results || []).map((item) => <div className="contrast-line" key={item.pair}><span>{item.pair.replaceAll('_', ' ')}</span><strong className={item.passed ? 'status-pass' : 'status-fail'}>{item.ratio ? `${item.ratio}:1` : '—'} {item.passed ? '✓' : '!'}</strong></div>)}</section>;
}

function Preview({ tokens, mode, setMode }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const root = ref.current;
    const colors = tokens.color || {};
    Object.entries({ '--preview-primary': colors.semantic?.primary, '--preview-accent': colors.semantic?.accent, '--preview-surface': colors.surface?.default, '--preview-panel': colors.surface?.panel, '--preview-text': colors.text?.primary, '--preview-muted': colors.text?.muted || colors.text?.tertiary, '--preview-border': colors.border?.default, '--preview-radius': tokens.radius?.md, '--preview-shadow': tokens.shadow?.elevation_2 }).forEach(([name, value]) => value && root.style.setProperty(name, value));
    root.style.setProperty('--preview-font', tokens.typography?.family?.body || 'Manrope');
  }, [tokens]);
  return <section className="software-ui-preview"><div className="preview-toolbar"><strong>Live preview</strong><select value={mode} onChange={(event) => setMode(event.target.value)} aria-label="Preview mode"><option value="dark">Dark</option><option value="light">Light</option><option value="high-contrast">High contrast</option></select></div><div className="preview-canvas" data-preview-root ref={ref} style={mode === 'light' ? { '--preview-surface': '#F8FAFC', '--preview-panel': '#FFFFFF', '--preview-text': '#111827', '--preview-border': '#CBD5E1' } : undefined}><article className="preview-card preview-kpi"><div><span className="preview-muted">Group revenue</span><strong>₹84.2L</strong><span className="status-pass">↗ 12.4% this period</span></div><span className="exec-icon-badge exec-icon-badge-gold exec-icon-badge-large">↗</span></article><article className="preview-card"><span className="preview-muted">Portfolio activity</span><table className="preview-table"><thead><tr><th>Company</th><th>Status</th><th>Score</th></tr></thead><tbody>{[['Vaidya Vihar', 'Healthy', '86'], ['Fresh Bowl', 'Watch', '72'], ['Urban Spice', 'Strong', '94']].map((row) => <tr key={row[0]}><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>)}</tbody></table></article><article className="preview-card preview-form"><span className="preview-muted">Component form</span><input placeholder="Executive decision title" aria-label="Preview title" /><select aria-label="Preview priority"><option>Priority · Medium</option><option>Priority · High</option></select><label><input type="checkbox" defaultChecked /> Notify leadership</label><div className="preview-buttons"><button type="button" className="preview-primary">Primary action</button><button type="button" className="preview-secondary">Cancel</button></div></article><article className="preview-card preview-modal"><strong>Decision review</strong><p className="preview-muted">This modal inherits the current surface, radius, border, and typography tokens.</p><div className="preview-buttons"><button type="button" className="preview-primary">Approve</button><button type="button">Review later</button></div></article><article className="preview-card preview-sidebar"><span className="preview-nav active">Overview</span><span className="preview-nav">Performance</span><span className="preview-nav">Governance</span><span className="preview-nav">Audit trail</span></article></div></section>;
}

export default function SoftwareUIPage() {
  const [profiles, setProfiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [theme, setTheme] = useState(null);
  const [version, setVersion] = useState(null);
  const [report, setReport] = useState(null);
  const [category, setCategory] = useState('Colors');
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState('');
  const [versions, setVersions] = useState([]);
  const [presets, setPresets] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const { state, dispatch, updateToken } = useTokenEditor(FALLBACK_TOKENS);

  useEffect(() => { themeApi.getProfileTypes().then((data) => { setProfiles(data.profile_types); setSelected(data.profile_types[0]); }).catch((error) => setToast(error.message)); themeApi.getPresets().then((data) => setPresets(data.presets)).catch(() => {}); }, []);
  useEffect(() => { if (!selected) return; themeApi.getThemes(selected.key).then(async (data) => { const next = data.themes.find((item) => item.is_default) || data.themes[0]; setTheme(next); if (next) { const result = await themeApi.getVersions(next.id); setVersions(result.versions); const published = result.versions.find((item) => item.id === next.current_version_id) || result.versions[0]; setVersion(published); dispatch({ type: 'LOAD_THEME', tokens: merge(FALLBACK_TOKENS, published?.tokens) }); } }).catch((error) => setToast(error.message)); }, [selected, dispatch]);
  useEffect(() => { let cancelled = false; const run = async () => { const result = await themeApi.validate(theme.id, state.tokens).catch(() => null); if (!cancelled && result) setReport(result.contrast); }; if (theme && state.tokens) run(); return () => { cancelled = true; }; }, [theme, state.tokens]);
  useEffect(() => { if (!state.dirty || !theme) return undefined; const timer = setTimeout(async () => { try { const saved = await themeApi.saveVersion(theme.id, state.tokens); setVersion(saved); setToast('Draft saved'); dispatch({ type: 'MARK_SAVED' }); } catch (error) { setToast(error.message); } }, 30000); return () => clearTimeout(timer); }, [state.dirty, state.tokens, theme, dispatch]);
  const reset = (path) => dispatch({ type: 'UPDATE_TOKEN', path, value: pathValue(FALLBACK_TOKENS, path) });
  const saveDraft = async () => { if (!theme) return; try { const saved = await themeApi.saveVersion(theme.id, state.tokens); setVersion(saved); setToast('Draft saved'); dispatch({ type: 'MARK_SAVED' }); } catch (error) { setToast(error.message); } };
  const validate = async () => { if (!theme) return; const result = await themeApi.validate(theme.id, state.tokens); setReport(result.contrast); setShowValidation(true); setToast(result.valid ? 'Validation passed' : 'Validation found issues'); };
  const publish = async () => { if (!theme || !version) return; if (report?.passed === false) { setToast('Publish blocked: fix contrast failures first'); return; } try { const published = await themeApi.publish(theme.id, version.id); setVersion(published); setToast('Theme published'); } catch (error) { setToast(error.response?.data?.detail?.message || error.message); } };
  const exportTheme = () => { const blob = new Blob([JSON.stringify({ theme, tokens: state.tokens, schema_version: '1.0' }, null, 2)], { type: 'application/json' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${selected?.key || 'profile'}-${theme?.slug || 'theme'}.json`; link.click(); URL.revokeObjectURL(link.href); };
  const importTheme = (event) => { const file = event.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { try { const payload = JSON.parse(reader.result); dispatch({ type: 'LOAD_THEME', tokens: merge(FALLBACK_TOKENS, payload.tokens) }); setToast('Imported tokens loaded as a draft'); } catch { setToast('Import failed: invalid theme JSON'); } }; reader.readAsText(file); event.target.value = ''; };
  const applyPreset = (preset) => { dispatch({ type: 'LOAD_THEME', tokens: merge(FALLBACK_TOKENS, preset.tokens) }); setToast(`${preset.name} loaded as a draft`); };
  const editor = category === 'Colors' ? <ColorEditor tokens={state.tokens} updateToken={updateToken} reset={reset} /> : <GenericEditor category={category.toLowerCase()} tokens={state.tokens} updateToken={updateToken} />;
  const statusText = useMemo(() => state.dirty ? 'Unsaved changes' : 'Saved', [state.dirty]);
  return <div className="software-ui-page">
    <header className="software-ui-bar"><div className="software-ui-heading"><h1>Software UI</h1><p><span className={state.dirty ? 'status-fail' : 'status-pass'}>●</span> {statusText} · {selected?.display_name || 'Loading profile type'}</p></div><div className="software-ui-theme-name"><span>Theme</span><strong>{theme?.name || 'Loading…'}</strong></div><div className="software-ui-actions"><button type="button" onClick={validate}>Validate</button><button type="button" onClick={saveDraft} disabled={!state.dirty}>Save draft</button><button type="button" onClick={() => setShowVersions(true)}>Version history</button><select aria-label="Apply preset" onChange={(event) => { const preset = presets.find((item) => item.id === event.target.value); if (preset) applyPreset(preset); }} defaultValue=""><option value="" disabled>Presets</option>{presets.map((preset) => <option value={preset.id} key={preset.id}>{preset.name}</option>)}</select><button type="button" onClick={exportTheme}>Export</button><label className="software-ui-import">Import<input type="file" accept="application/json" onChange={importTheme} /></label><button type="button" className="primary" onClick={publish}>Publish</button></div></header>
    <div className="software-ui-layout"><ProfileRail profiles={profiles} selected={selected} onSelect={setSelected} search={search} onSearch={setSearch} /><main className="software-ui-editor"><div className="category-tabs" role="tablist">{categoryLabels.map((label) => <button type="button" role="tab" aria-selected={category === label} className={category === label ? 'active' : ''} key={label} onClick={() => setCategory(label)}>{label}</button>)}</div><div className="editor-section-title"><h2>{category}</h2><small>{state.past.length} edits · Cmd+Z undo</small></div>{editor}<AccessibilityPanel report={report} /></main><Preview tokens={state.tokens} mode={state.mode} setMode={(mode) => dispatch({ type: 'SET_MODE', mode })} /></div>
    {showVersions && <div className="command-palette-backdrop" role="presentation" onClick={() => setShowVersions(false)}><section className="command-palette" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><div className="command-palette-header">Version history <button type="button" onClick={() => setShowVersions(false)}>×</button></div>{versions.map((item) => <div className="command-result" key={item.id}><span>v{item.version_number} · {item.status}</span><small>{item.change_summary || 'Token snapshot'}</small><button type="button" onClick={() => { dispatch({ type: 'LOAD_THEME', tokens: merge(FALLBACK_TOKENS, item.tokens) }); setShowVersions(false); }}>Preview</button></div>)}</section></div>}
    {showValidation && <div className="command-palette-backdrop" role="presentation" onClick={() => setShowValidation(false)}><section className="command-palette validation-dialog" role="dialog" aria-modal="true" aria-labelledby="validation-title" onClick={(event) => event.stopPropagation()}><div className="command-palette-header"><span id="validation-title">Contrast validation</span><button type="button" onClick={() => setShowValidation(false)} aria-label="Close validation">×</button></div><div className="validation-dialog-summary">{report?.passed ? '✓ WCAG AA contrast passing' : '⚠ Contrast needs attention'}</div>{(report?.results || []).map((item) => <div className="contrast-line" key={item.pair}><span>{item.pair.replaceAll('_', ' ')}</span><strong className={item.passed ? 'status-pass' : 'status-fail'}>{item.ratio ? `${item.ratio}:1` : '—'} {item.passed ? '✓ Pass' : '! Fail'}</strong></div>)}</section></div>}
    {toast && <button type="button" className="software-ui-toast" onClick={() => setToast('')}>{toast}</button>}
  </div>;
}
