import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileText, HeartPulse, LineChart, Utensils } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import type { AgentId } from './components/Sidebar';
import { ChatView } from './components/ChatView';
import type { ChatMessage } from './components/ChatView';
import { ArtifactsLibraryView } from './components/ArtifactsLibraryView';
import { AccountView } from './components/AccountView';
import { AgentLandingView } from './components/AgentLandingView';
import { PlansView } from './components/PlansView';
import './App.css';

interface UserPublic {
  id: string;
  email: string;
  created_at: string;
}

interface SessionSummary {
  id: string;
  agent_id: AgentId;
  title: string;
  created_at: string;
  updated_at: string;
}

type ArtifactCategory =
  | 'cpet_report'
  | 'exercise_data'
  | 'health_data'
  | 'diet_data'
  | 'lab_report'
  | 'imaging_report'
  | 'other';

interface ArtifactListItem {
  id: string;
  category: ArtifactCategory;
  title?: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  has_extracted_text: boolean;
  has_parsed_json: boolean;
}

interface SessionDetail {
  id: string;
  agent_id: AgentId;
  title: string;
  created_at: string;
  updated_at: string;
  messages: { id: string; role: 'user' | 'assistant'; content: string; created_at: string }[];
  artifacts: ArtifactListItem[];
}

type PlanType = 'exercise' | 'nutrition';

interface PlanDraft {
  id: string;
  planType: PlanType;
  summary: string;
  payload: Record<string, unknown>;
  warnings: string[];
  status: 'draft' | 'confirmed';
}

const apiBase = import.meta.env.VITE_API_BASE ?? '';

const agentMeta: Record<
  AgentId,
  { label: string; description: string; placeholder: string; category: ArtifactCategory }
> = {
  report: {
    label: 'CPET 报告解读',
    description: '引用你的历史 CPET 报告/结果，也支持新上传报告进行解读。',
    placeholder: '上传 CPET 报告或直接提问…',
    category: 'cpet_report',
  },
  analysis: {
    label: '运动数据分析',
    description: '结合历史运动/健康数据与新上传文件，生成趋势与建议。',
    placeholder: '上传运动/手表数据或直接提问…',
    category: 'exercise_data',
  },
  health: {
    label: '健康风险评估',
    description: '基于历史健康数据与报告，输出风险提示与管理建议。',
    placeholder: '描述你的情况或上传检查结果…',
    category: 'health_data',
  },
  diet: {
    label: '营养食疗建议',
    description: '结合饮食记录与健康风险，给出可执行的饮食/食疗建议。',
    placeholder: '上传饮食记录或描述饮食目标…',
    category: 'diet_data',
  },
  clinical: {
    label: '临床智能体',
    description: '面向临床问题的智能问答与决策辅助。',
    placeholder: '输入问题…',
    category: 'other',
  },
  prescription: {
    label: '运动处方',
    description: '基于 CPET 指标生成个体化运动处方。',
    placeholder: '上传 CPET 结果并提出诉求…',
    category: 'cpet_report',
  },
};

const collectTextParts = (parts: unknown[]) => {
  const texts: string[] = [];
  parts.forEach((part) => {
    if (typeof part !== 'object' || part === null || Array.isArray(part)) {
      return;
    }
    const obj = part as Record<string, unknown>;
    if (obj.type === 'text' && typeof obj.text === 'string') {
      texts.push(obj.text);
    }
  });
  return texts.join('');
};

const extractOpenCodeText = (payload: unknown) => {
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    return '';
  }
  const obj = payload as Record<string, unknown>;
  if (typeof obj.answer === 'string') {
    return obj.answer;
  }
  if (Array.isArray(obj.parts)) {
    return collectTextParts(obj.parts as unknown[]);
  }
  const msg = obj.message as Record<string, unknown> | undefined;
  if (msg && Array.isArray(msg.parts)) {
    return collectTextParts(msg.parts as unknown[]);
  }
  const data = obj.data as Record<string, unknown> | undefined;
  if (data && Array.isArray(data.parts)) {
    return collectTextParts(data.parts as unknown[]);
  }
  return '';
};

const extractOpenCodeError = (payload: unknown) => {
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    return '';
  }
  const obj = payload as Record<string, unknown>;
  const err = obj.error as Record<string, unknown> | undefined;
  if (err) {
    const msg = err.message ?? err.detail ?? err.error;
    if (typeof msg === 'string' && msg.trim()) {
      return msg.trim();
    }
  }
  const info = obj.info as Record<string, unknown> | undefined;
  if (info) {
    const infoErr = info.error as Record<string, unknown> | undefined;
    if (infoErr) {
      const data = infoErr.data as Record<string, unknown> | undefined;
      const msg = (data && data.message) ?? infoErr.message ?? infoErr.detail;
      if (typeof msg === 'string' && msg.trim()) {
        return msg.trim();
      }
    }
  }
  return '';
};

const readOpenCodeResponse = async (response: Response, onStream?: (text: string) => void) => {
  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('text/event-stream')) {
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';
    let streamError: string | null = null;

    const handleLine = (line: string) => {
      if (!line.startsWith('data:')) {
        return;
      }
      const jsonStr = line.slice(5).trim();
      if (!jsonStr || jsonStr === '[DONE]') {
        return;
      }
      try {
        const event = JSON.parse(jsonStr);
        const err = extractOpenCodeError(event);
        if (err) {
          streamError = err;
          return;
        }
        if (event?.parts && Array.isArray(event.parts)) {
          const delta = collectTextParts(event.parts);
          if (delta) {
            fullText += delta;
            onStream?.(fullText);
          }
        } else {
          const maybeText = extractOpenCodeText(event);
          if (maybeText) {
            fullText = maybeText;
            onStream?.(fullText);
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        handleLine(line);
        if (streamError) {
          break;
        }
      }
      if (streamError) {
        break;
      }
    }
    if (buffer && !streamError) {
      handleLine(buffer);
    }
    if (streamError) {
      try {
        await reader.cancel();
      } catch {
        // ignore
      }
      throw new Error(streamError);
    }
    return fullText;
  }

  const raw = await response.text();
  if (contentType.includes('application/json') || raw.trim().startsWith('{')) {
    try {
      const data = JSON.parse(raw);
      const err = extractOpenCodeError(data);
      if (err) {
        throw new Error(err);
      }
      const extracted = extractOpenCodeText(data);
      return extracted || '';
    } catch {
      // fall through
    }
  }
  return raw;
};

const toLocalTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
};

async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${apiBase}${path}`, {
    credentials: 'include',
    ...init,
  });
}

function App() {
  const [me, setMe] = useState<UserPublic | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [chatError, setChatError] = useState<{ message: string; at: string } | null>(null);
  const [planGenerating, setPlanGenerating] = useState(false);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState<'chat' | 'library' | 'plans' | 'account'>('chat');
  const [activeAgentId, setActiveAgentId] = useState<AgentId>('report');
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<SessionDetail | null>(null);

  const [streamingContent, setStreamingContent] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [planDraftsBySession, setPlanDraftsBySession] = useState<Record<string, PlanDraft[]>>({});

  const agents = useMemo(
    () => [
      { id: 'report' as const, label: agentMeta.report.label, icon: <FileText className="w-4 h-4" /> },
      { id: 'analysis' as const, label: agentMeta.analysis.label, icon: <LineChart className="w-4 h-4" /> },
      { id: 'health' as const, label: agentMeta.health.label, icon: <HeartPulse className="w-4 h-4" /> },
      { id: 'diet' as const, label: agentMeta.diet.label, icon: <Utensils className="w-4 h-4" /> },
    ],
    []
  );

  const sidebarSessions = useMemo(
    () =>
      sessions
        .filter((s) => s.agent_id === activeAgentId)
        .map((s) => ({ id: s.id, title: s.title, agentId: s.agent_id })),
    [activeAgentId, sessions]
  );

  const refreshMe = useCallback(async () => {
    try {
      const resp = await apiFetch('/api/auth/me');
      if (!resp.ok) {
        setMe(null);
        return;
      }
      const data = (await resp.json()) as UserPublic;
      setMe(data);
    } finally {
      setAuthChecked(true);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const handleAuthSubmit = async () => {
    setAuthError(null);
    setAuthLoading(true);
    try {
      const endpoint = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const resp = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `登录失败 (${resp.status})`);
      }
      await refreshMe();
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } finally {
      setMe(null);
      setSessions([]);
      setActiveSessionId(null);
      setActiveSession(null);
      setActiveView('chat');
      setPlanDraftsBySession({});
      setChatError(null);
    }
  };

  const loadSessions = useCallback(async (agentId: AgentId) => {
    const resp = await apiFetch(`/api/chat/sessions?agent_id=${encodeURIComponent(agentId)}`);
    if (!resp.ok) {
      throw new Error(`Failed to load sessions (${resp.status})`);
    }
    const data = (await resp.json()) as { items: SessionSummary[] };
    setSessions(data.items ?? []);
    return data.items ?? [];
  }, []);

  const loadSessionPlans = useCallback(async (sessionId: string) => {
    try {
      const resp = await apiFetch(`/api/plans/session/${encodeURIComponent(sessionId)}?status=draft`);
      if (!resp.ok) {
        return;
      }
      const data = (await resp.json()) as {
        items: {
          plan_id: string;
          plan_type: PlanType;
          summary: string;
          payload: Record<string, unknown>;
          status: 'draft' | 'confirmed';
        }[];
      };
      const mapped: PlanDraft[] = (data.items ?? []).map((item) => ({
        id: item.plan_id,
        planType: item.plan_type,
        summary: item.summary,
        payload: item.payload ?? {},
        warnings: [],
        status: item.status ?? 'draft',
      }));
      setPlanDraftsBySession((prev) => ({ ...prev, [sessionId]: mapped }));
    } catch {
      // ignore
    }
  }, []);

  const loadSessionDetail = useCallback(async (sessionId: string) => {
    const resp = await apiFetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`);
    if (!resp.ok) {
      throw new Error(`Failed to load session (${resp.status})`);
    }
    const data = (await resp.json()) as SessionDetail;
    setActiveSession(data);
    void loadSessionPlans(sessionId);
    return data;
  }, [loadSessionPlans]);

  const createNewSession = useCallback(async (agentId: AgentId) => {
    const resp = await apiFetch('/api/chat/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, title: '新会话' }),
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `Failed to create session (${resp.status})`);
    }
    const session = (await resp.json()) as { id: string };
    setActiveSessionId(session.id);
    await loadSessions(agentId);
    await loadSessionDetail(session.id);
    return session.id;
  }, [loadSessionDetail, loadSessions]);

  // After login or when switching agent, load sessions and open the latest one (or create).
  useEffect(() => {
    if (!me) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const items = await loadSessions(activeAgentId);
        if (cancelled) return;
        if (items.length > 0) {
          setActiveSessionId(items[0].id);
          await loadSessionDetail(items[0].id);
        } else {
          await createNewSession(activeAgentId);
        }
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeAgentId, createNewSession, loadSessionDetail, loadSessions, me]);

  const handleSelectAgent = (agentId: AgentId) => {
    setActiveAgentId(agentId);
    setActiveSessionId(null);
    setActiveSession(null);
    setStreamingContent('');
    setIsThinking(false);
    setChatError(null);
    abortControllerRef.current?.abort();
    setActiveView('chat');
  };

  const handleNewSession = () => {
    if (!me) return;
    setActiveView('chat');
    setChatError(null);
    void createNewSession(activeAgentId);
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setChatError(null);
    void loadSessionDetail(sessionId);
    setActiveView('chat');
  };

  const handleStop = () => {
    abortControllerRef.current?.abort();
  };

  const handleSend = async (content: string) => {
    if (!me) return;
    const sessionId = activeSessionId ?? (await createNewSession(activeAgentId));
    setChatError(null);

    // Optimistic user message
    setActiveSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        messages: [
          ...prev.messages,
          { id: `local-${Date.now()}`, role: 'user', content, created_at: new Date().toISOString() },
        ],
      };
    });

    setIsThinking(true);
    setStreamingContent('');

    // Cancel any previous request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const resp = await apiFetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream, application/json',
        },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });
      if (!resp.ok) {
        const text = await resp.text();
        let message = text;
        if (text) {
          try {
            const payload = JSON.parse(text);
            if (typeof payload?.detail === 'string') {
              message = payload.detail;
            } else if (typeof payload?.error === 'string') {
              message = payload.error;
            }
          } catch {
            // ignore parse errors
          }
        }
        throw new Error(message || `请求失败 (${resp.status})`);
      }
      const answer = await readOpenCodeResponse(resp, (txt) => setStreamingContent(txt));
      if (answer.trim()) {
        setActiveSession((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            messages: [
              ...prev.messages,
              { id: `local-a-${Date.now()}`, role: 'assistant', content: answer, created_at: new Date().toISOString() },
            ],
          };
        });
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        return;
      }
      const msg = err instanceof Error ? err.message : '未知错误';
      setChatError({ message: msg, at: new Date().toISOString() });
    } finally {
      setIsThinking(false);
      setStreamingContent('');
      abortControllerRef.current = null;
      // Refresh canonical state from server (messages + attachments + title).
      try {
        await loadSessions(activeAgentId);
        await loadSessionDetail(sessionId);
      } catch {
        // ignore
      }
    }
  };

  const handleConfirmPlan = async (draftId: string) => {
    if (!me) return;
    try {
      const resp = await apiFetch('/api/plans/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `确认失败 (${resp.status})`);
      }
      const data = (await resp.json()) as { status: 'draft' | 'confirmed' };
      const sessionId = activeSessionId;
      if (!sessionId) return;
      void loadSessionPlans(sessionId);
      setPlanDraftsBySession((prev) => {
        const existing = prev[sessionId] ?? [];
        const next = existing.map((draft) =>
          draft.id === draftId ? { ...draft, status: data.status ?? 'confirmed' } : draft
        );
        return { ...prev, [sessionId]: next };
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : '确认失败';
      console.warn('confirm plan failed', msg);
    }
  };

  const handleGenerateExercisePlan = async () => {
    if (!me || planGenerating) return;
    setPlanGenerating(true);
    setChatError(null);
    try {
      const sessionId = activeSessionId ?? (await createNewSession(activeAgentId));
      const resp = await apiFetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'generate_exercise_plan',
          arguments: {
            patient_id: me.id,
            session_id: sessionId,
            save_plan: true,
            confirm_plan: false,
            source_session_id: sessionId,
          },
        }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `生成失败 (${resp.status})`);
      }
      const data = (await resp.json()) as { error?: string | null };
      if (data?.error) {
        throw new Error(data.error);
      }
      await loadSessionPlans(sessionId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '生成失败';
      setChatError({ message: msg, at: new Date().toISOString() });
    } finally {
      setPlanGenerating(false);
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!me || !files || files.length === 0) return;
    const sessionId = activeSessionId ?? (await createNewSession(activeAgentId));
    const category = agentMeta[activeAgentId].category;
    for (const file of Array.from(files)) {
      const form = new FormData();
      form.append('category', category);
      form.append('attach_session_id', sessionId);
      form.append('file', file);
      try {
        const resp = await apiFetch('/api/artifacts/upload', { method: 'POST', body: form });
        if (!resp.ok) {
          // best-effort
          console.log('upload failed', await resp.text());
        }
      } catch {
        // ignore
      }
    }
    try {
      await loadSessionDetail(sessionId);
    } catch {
      // ignore
    }
  };

  const handleRemoveUpload = async (artifactId: string) => {
    if (!me || !activeSessionId) return;
    await apiFetch(`/api/chat/sessions/${encodeURIComponent(activeSessionId)}/artifacts/${encodeURIComponent(artifactId)}`, {
      method: 'DELETE',
    });
    await loadSessionDetail(activeSessionId);
  };

  const chatMessages: ChatMessage[] = useMemo(() => {
    const rows = activeSession?.messages ?? [];
    return rows.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: toLocalTime(m.created_at),
    }));
  }, [activeSession?.messages]);

  const uploadedFiles = useMemo(
    () =>
      (activeSession?.artifacts ?? []).map((a) => ({
        id: a.id,
        name: a.filename,
        status: a.has_parsed_json ? 'parsed' : 'raw',
      })),
    [activeSession?.artifacts]
  );

  const attachedArtifactIds = useMemo(() => {
    return new Set((activeSession?.artifacts ?? []).map((a) => a.id));
  }, [activeSession?.artifacts]);

  const activePlanDrafts = useMemo(() => {
    if (!activeSessionId) return [];
    return planDraftsBySession[activeSessionId] ?? [];
  }, [activeSessionId, planDraftsBySession]);

  const refreshActiveSession = useCallback(async () => {
    if (!activeSessionId) return;
    await loadSessions(activeAgentId);
    await loadSessionDetail(activeSessionId);
  }, [activeAgentId, activeSessionId, loadSessionDetail, loadSessions]);

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">
        加载中…
      </div>
    );
  }

  if (!me) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center px-6">
        <div className="w-full max-w-sm border border-gray-200 rounded-2xl p-6">
          <div className="text-lg font-semibold text-gray-900">心慧智问</div>
          <div className="text-xs text-gray-500 mt-1">
            {authMode === 'register' ? '注册后才能使用服务' : '登录后才能使用服务'}
          </div>

          <div className="mt-6 space-y-3">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="邮箱"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-gray-300"
              autoComplete="email"
            />
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码（至少 8 位）"
              type="password"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-gray-300"
              autoComplete={authMode === 'register' ? 'new-password' : 'current-password'}
            />
            {authError && <div className="text-xs text-red-500">{authError}</div>}
            <button
              type="button"
              onClick={handleAuthSubmit}
              disabled={authLoading}
              className="w-full bg-black text-white rounded-lg px-3 py-2 text-sm disabled:opacity-50"
            >
              {authLoading ? '处理中…' : authMode === 'register' ? '注册' : '登录'}
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMode((m) => (m === 'login' ? 'register' : 'login'));
                setAuthError(null);
              }}
              className="w-full border border-gray-200 text-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              {authMode === 'login' ? '没有账号？去注册' : '已有账号？去登录'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const agent = agentMeta[activeAgentId];
  const showLanding =
    activeView === 'chat' &&
    (activeSession?.messages?.length ?? 0) === 0 &&
    !isThinking &&
    !streamingContent &&
    !chatError;
  const headerTitle =
    activeView === 'library'
      ? '我的资料库'
      : activeView === 'plans'
        ? '运动与营养规划'
        : activeView === 'account'
          ? '账号与合规'
          : agent.label;
  const headerDesc =
    activeView === 'library'
      ? '查看/上传你的报告与数据，可一键附加到当前会话供智能体引用。'
      : activeView === 'plans'
        ? '展示最近确认的运动处方与营养规划。'
        : activeView === 'account'
          ? '管理账户信息与 API Key。'
          : agent.description;

  return (
    <div className="min-h-screen bg-white flex">
      <Sidebar
        agents={agents}
        activeAgentId={activeAgentId}
        activeView={activeView}
        sessions={sidebarSessions}
        activeSessionId={activeSessionId}
        onSelectAgent={handleSelectAgent}
        onSelectView={(v) => setActiveView(v)}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
      />

      <main
        className={`flex-1 min-h-screen min-h-0 flex flex-col ${sidebarCollapsed ? 'ml-[72px]' : 'ml-[240px]'}`}
      >
        {!showLanding && (
          <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              <span className="font-medium text-gray-900">{headerTitle}</span>
              <span className="ml-2 text-gray-400">{headerDesc}</span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs px-2.5 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-gray-300"
            >
              退出登录
            </button>
          </div>
        )}

        {activeView === 'library' ? (
          <ArtifactsLibraryView
            activeSessionId={activeSessionId}
            attachedArtifactIds={attachedArtifactIds}
            onAttachmentsChanged={refreshActiveSession}
            defaultCategory={agentMeta[activeAgentId].category}
          />
        ) : activeView === 'plans' ? (
          <PlansView userId={me.id} />
        ) : activeView === 'account' ? (
          <AccountView user={me} />
        ) : showLanding ? (
          <div className="flex-1 flex flex-col">
            <div className="px-6 py-4 flex justify-end">
              <button
                type="button"
                onClick={handleLogout}
                className="text-xs px-2.5 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-gray-300"
              >
                退出登录
              </button>
            </div>
            <AgentLandingView
              title="心慧智问"
              agentLabel={agent.label}
              placeholder={agent.placeholder}
              onSend={handleSend}
              onUpload={handleUpload}
              onRemoveUpload={handleRemoveUpload}
              uploadedFiles={uploadedFiles}
            />
          </div>
        ) : (
          <ChatView
            messages={chatMessages}
            agentId={activeAgentId}
            agentLabel={agent.label}
            placeholder={agent.placeholder}
            sessionTitle={activeSession?.title}
            onSend={handleSend}
            onUpload={handleUpload}
            onRemoveUpload={handleRemoveUpload}
            onStop={handleStop}
            uploadedFiles={uploadedFiles}
            isThinking={isThinking}
            streamingContent={streamingContent}
            errorMessage={chatError?.message ?? null}
            onClearError={() => setChatError(null)}
            pdfSuggestion={null}
            pdfDefaults={null}
            planDrafts={activePlanDrafts}
            onConfirmPlan={handleConfirmPlan}
            onGenerateExercisePlan={handleGenerateExercisePlan}
          />
        )}
      </main>
    </div>
  );
}

export default App;
