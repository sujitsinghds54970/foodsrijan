import { useCallback, useReducer } from 'react';

const clone = (value: any) => JSON.parse(JSON.stringify(value || {}));
const getPath = (object: any, path: string) => path.split('.').reduce((value, key) => value?.[key], object);
const setPath = (object: any, path: string, value: any) => {
  const result = clone(object);
  const keys = path.split('.');
  let cursor = result;
  keys.slice(0, -1).forEach((key) => { cursor[key] = cursor[key] || {}; cursor = cursor[key]; });
  cursor[keys[keys.length - 1]] = value;
  return result;
};

function reducer(state: any, action: any) {
  if (action.type === 'LOAD_THEME') return { ...state, tokens: clone(action.tokens), initial: clone(action.tokens), past: [], future: [], dirty: false };
  if (action.type === 'UPDATE_TOKEN') return { ...state, tokens: setPath(state.tokens, action.path, action.value), past: [...state.past.slice(-49), state.tokens], future: [], dirty: true };
  if (action.type === 'UPDATE_TOKENS_BATCH') return { ...state, tokens: { ...state.tokens, ...action.tokens }, past: [...state.past.slice(-49), state.tokens], future: [], dirty: true };
  if (action.type === 'UNDO' && state.past.length) return { ...state, tokens: state.past[state.past.length - 1], past: state.past.slice(0, -1), future: [state.tokens, ...state.future], dirty: true };
  if (action.type === 'REDO' && state.future.length) return { ...state, tokens: state.future[0], past: [...state.past, state.tokens], future: state.future.slice(1), dirty: true };
  if (action.type === 'RESET_SECTION') {
    const tokens = { ...state.tokens, [action.section]: clone(state.initial[action.section]) };
    return { ...state, tokens, past: [...state.past.slice(-49), state.tokens], future: [], dirty: true };
  }
  if (action.type === 'SET_MODE') return { ...state, mode: action.mode };
  if (action.type === 'MARK_SAVED') return { ...state, dirty: false };
  return state;
}
export function useTokenEditor(initialTokens: Record<string, any> = {}) {
  const [state, dispatch] = useReducer(reducer, { tokens: clone(initialTokens), initial: clone(initialTokens), past: [], future: [], dirty: false, mode: 'dark' });
  const updateToken = useCallback((path: string, value: any) => dispatch({ type: 'UPDATE_TOKEN', path, value }), []);
  return { state, dispatch, updateToken, getToken: (path: string) => getPath(state.tokens, path) };
}
