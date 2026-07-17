import { useState, type FormEvent } from 'react';

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
  error: string | null;
  busy: boolean;
}

export function LoginScreen({ onLogin, onRegister, error, busy }: LoginScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    const name = username.trim();
    if (name.length < 3) {
      setLocalError('Username must be at least 3 characters.');
      return;
    }
    if (password.length < 4) {
      setLocalError('Password must be at least 4 characters.');
      return;
    }
    try {
      if (mode === 'login') {
        await onLogin(name, password);
      } else {
        await onRegister(name, password);
      }
    } catch {
      /* error shown via props */
    }
  };

  const displayError = localError ?? error;

  return (
    <div className="login-screen">
      <div className="login-card">
        <p className="login-card__eyebrow">Pathology DES</p>
        <h1>Simulation Lab</h1>
        <p className="login-card__lead">
          Sign in with a username to keep your runs and results separate from other users.
        </p>

        <div className="segmented login-card__tabs">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}
            disabled={busy}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'active' : ''}
            onClick={() => setMode('register')}
            disabled={busy}
          >
            Create account
          </button>
        </div>

        <form className="login-form" onSubmit={(e) => void submit(e)}>
          <label>
            Username
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. varad"
              disabled={busy}
              spellCheck={false}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 4 characters"
              disabled={busy}
            />
          </label>
          {displayError ? <p className="login-form__error">{displayError}</p> : null}
          <button type="submit" className="run-button" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>

        <p className="login-card__note muted">
          Prototype identity only — passwords are stored for file scoping, not as secure authentication.
        </p>
      </div>
    </div>
  );
}
